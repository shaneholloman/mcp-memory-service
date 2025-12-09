#!/usr/bin/env python3
"""
Re-score memories with fallback MS-MARCO + DeBERTa approach.

This script re-evaluates all DeBERTa-scored memories using the new fallback
approach: DeBERTa primary with MS-MARCO rescue for technical content.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.config import SQLITE_VEC_PATH
from mcp_memory_service.quality.onnx_ranker import get_onnx_ranker_model

# Default thresholds (can be overridden via environment variables)
DEFAULT_DEBERTA_THRESHOLD = 0.6
DEFAULT_MS_MARCO_THRESHOLD = 0.7


async def rescore_fallback(
    dry_run=True,
    deberta_threshold=DEFAULT_DEBERTA_THRESHOLD,
    ms_marco_threshold=DEFAULT_MS_MARCO_THRESHOLD
):
    """
    Re-score all DeBERTa memories with fallback approach.

    Args:
        dry_run: If True, only report what would change (default)
        deberta_threshold: DeBERTa confidence threshold (default: 0.6)
        ms_marco_threshold: MS-MARCO rescue threshold (default: 0.7)
    """
    print("=" * 80)
    print(f"Fallback Re-scoring - {'DRY RUN' if dry_run else 'LIVE MODE'}")
    print("=" * 80)
    print(f"DeBERTa threshold: {deberta_threshold}")
    print(f"MS-MARCO threshold: {ms_marco_threshold}")
    print()

    # Load both models
    print("Loading models...")
    deberta = get_onnx_ranker_model('nvidia-quality-classifier-deberta', 'auto')
    ms_marco = get_onnx_ranker_model('ms-marco-MiniLM-L-6-v2', 'auto')

    if not deberta or not ms_marco:
        print("❌ Failed to load both models")
        print()
        if not deberta:
            print("  DeBERTa model not available")
        if not ms_marco:
            print("  MS-MARCO model not available")
        return

    print(f"✓ DeBERTa loaded")
    print(f"✓ MS-MARCO loaded")
    print()

    # Connect to storage
    print("Connecting to database...")
    storage = SqliteVecMemoryStorage(SQLITE_VEC_PATH)
    await storage.initialize()
    print(f"✓ Connected to: {SQLITE_VEC_PATH}")
    print()

    # Get DeBERTa-scored memories
    all_memories = await storage.get_all_memories()
    to_rescore = [
        m for m in all_memories
        if m.metadata and m.metadata.get('quality_provider') == 'onnx_deberta'
    ]

    print(f"Total memories: {len(all_memories)}")
    print(f"Memories to re-score: {len(to_rescore)} (onnx_deberta only)")
    print()

    if len(to_rescore) == 0:
        print("✓ No memories to re-score!")
        return

    improvements = []
    decision_counts = {
        'deberta_confident': 0,
        'ms_marco_rescue': 0,
        'both_low': 0
    }

    print("Re-scoring memories...")
    print()

    for i, memory in enumerate(to_rescore, 1):
        old_score = memory.metadata.get('quality_score', 0.5)

        # Step 1: Score with DeBERTa (query-independent)
        deberta_score = deberta.score_quality("", memory.content)

        # Step 2: Apply fallback logic
        if deberta_score >= deberta_threshold:
            # DeBERTa confident - use it
            final_score = deberta_score
            decision = 'deberta_confident'
            ms_marco_score = None
        else:
            # DeBERTa low - try MS-MARCO rescue
            # Use empty query to avoid self-matching bias
            ms_marco_score = ms_marco.score_quality("", memory.content)

            if ms_marco_score >= ms_marco_threshold:
                # MS-MARCO rescue
                final_score = ms_marco_score
                decision = 'ms_marco_rescue'
            else:
                # Both agree low
                final_score = deberta_score
                decision = 'both_low'

        decision_counts[decision] += 1
        delta = final_score - old_score

        # Track significant changes (>0.1 difference)
        if abs(delta) > 0.1:
            improvements.append({
                'content': memory.content[:80].replace('\n', ' '),
                'old': old_score,
                'deberta': deberta_score,
                'ms_marco': ms_marco_score,
                'final': final_score,
                'decision': decision,
                'delta': delta,
                'hash': memory.content_hash
            })

        if not dry_run:
            # Build quality_components dict
            components = {
                'final_score': final_score,
                'deberta_score': deberta_score,
                'decision': decision
            }
            if ms_marco_score is not None:
                components['ms_marco_score'] = ms_marco_score

            # Update memory metadata
            await storage.update_memory_metadata(
                content_hash=memory.content_hash,
                updates={
                    'quality_score': final_score,
                    'quality_provider': 'fallback_deberta-msmarco',
                    'quality_components': components
                }
            )

        # Progress indicator
        if i % 100 == 0:
            ms_str = f"M:{ms_marco_score:.3f}" if ms_marco_score else "M:N/A"
            print(
                f"  [{i:5d}/{len(to_rescore)}] {decision[:4].upper()} | "
                f"Final: {final_score:.3f} (D:{deberta_score:.3f}, {ms_str})"
            )

    # Report decision distribution
    print()
    print("=" * 80)
    print("Decision Distribution")
    print("=" * 80)
    for decision, count in decision_counts.items():
        pct = (count / len(to_rescore)) * 100 if to_rescore else 0
        print(f"{decision:20s}: {count:5d} ({pct:5.1f}%)")
    print()

    # Report top improvements
    print("=" * 80)
    print("Top Improvements (fallback vs DeBERTa-only)")
    print("=" * 80)

    improvements.sort(key=lambda x: -x['delta'])
    for imp in improvements[:15]:
        ms_str = f"M:{imp['ms_marco']:.3f}" if imp['ms_marco'] else "M:N/A"
        print(
            f"Delta: {imp['delta']:+.3f} | Old: {imp['old']:.3f} → "
            f"New: {imp['final']:.3f} ({imp['decision']})"
        )
        print(f"  DeBERTa: {imp['deberta']:.3f}, {ms_str}")
        print(f"  {imp['content']}")
        print()

    if dry_run:
        print("=" * 80)
        print("DRY RUN COMPLETE - No changes made")
        print("=" * 80)
        print()
        print("To execute re-scoring, run:")
        print(f"  python {__file__} --execute")
        print()
        print("To adjust thresholds:")
        print(f"  python {__file__} --execute --deberta-threshold 0.5 --msmarco-threshold 0.6")
        return

    # Execute mode - create log
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print()

    log_path = Path.home() / 'backups/mcp-memory-service' / \
        f'rescore-fallback-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, 'w') as log:
        log.write(f"Fallback re-scoring executed: {datetime.now()}\n")
        log.write(f"DeBERTa threshold: {deberta_threshold}\n")
        log.write(f"MS-MARCO threshold: {ms_marco_threshold}\n")
        log.write(f"Total re-scored: {len(to_rescore)}\n\n")

        log.write("Decision Distribution:\n")
        for decision, count in decision_counts.items():
            pct = (count / len(to_rescore)) * 100 if to_rescore else 0
            log.write(f"  {decision:20s}: {count:5d} ({pct:5.1f}%)\n")
        log.write("\n")

        log.write("Top Improvements:\n")
        for imp in improvements[:50]:  # Log top 50
            log.write(
                f"{imp['hash']}\t{imp['old']:.4f}\t{imp['final']:.4f}\t"
                f"{imp['delta']:+.4f}\t{imp['decision']}\n"
            )

    print(f"✓ Updated: {len(to_rescore)} memories")
    print(f"  DeBERTa confident: {decision_counts['deberta_confident']}")
    print(f"  MS-MARCO rescue: {decision_counts['ms_marco_rescue']}")
    print(f"  Both low: {decision_counts['both_low']}")
    print()
    print(f"📝 Log saved: {log_path}")
    print()

    # Verify final state
    remaining = await storage.get_all_memories()
    fallback_count = sum(
        1 for m in remaining
        if m.metadata and m.metadata.get('quality_provider') == 'fallback_deberta-msmarco'
    )
    print(f"Database state:")
    print(f"  Total memories: {len(remaining)}")
    print(f"  Fallback-scored: {fallback_count}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Re-score memories with DeBERTa + MS-MARCO fallback approach"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help="Execute re-scoring (default: dry-run only)"
    )
    parser.add_argument(
        '--deberta-threshold',
        type=float,
        default=DEFAULT_DEBERTA_THRESHOLD,
        help=f"DeBERTa confidence threshold (default: {DEFAULT_DEBERTA_THRESHOLD})"
    )
    parser.add_argument(
        '--msmarco-threshold',
        type=float,
        default=DEFAULT_MS_MARCO_THRESHOLD,
        help=f"MS-MARCO rescue threshold (default: {DEFAULT_MS_MARCO_THRESHOLD})"
    )

    args = parser.parse_args()

    asyncio.run(rescore_fallback(
        dry_run=not args.execute,
        deberta_threshold=args.deberta_threshold,
        ms_marco_threshold=args.msmarco_threshold
    ))
