#!/usr/bin/env python3
"""
Safe cleanup of very low quality memories (<0.1 score).

Removes document fragments, page numbers, and corrupted PDF text
identified by DeBERTa quality scoring.
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.config import SQLITE_VEC_PATH

# Safety thresholds
QUALITY_THRESHOLD = 0.1  # Only delete memories scoring below this
MIN_LENGTH_EXCEPTION = 100  # Keep memories >100 chars even if low quality
PRESERVE_TYPES = ['test', 'troubleshooting']  # Never delete these types

async def cleanup_low_quality(dry_run=True):
    """
    Cleanup very low quality memories with safety checks.

    Args:
        dry_run: If True, only report what would be deleted (default)
    """
    print("=" * 80)
    print(f"Low Quality Memory Cleanup - {'DRY RUN' if dry_run else 'LIVE MODE'}")
    print("=" * 80)
    print()

    # Connect to storage
    print("Connecting to database...")
    storage = SqliteVecMemoryStorage(SQLITE_VEC_PATH)
    await storage.initialize()

    print(f"✓ Connected to: {SQLITE_VEC_PATH}")
    print()

    # Fetch all memories
    print("Fetching all memories...")
    all_memories = await storage.get_all_memories()
    print(f"✓ Total memories: {len(all_memories)}")
    print()

    # Identify cleanup candidates
    candidates = []
    preserved = {
        'high_quality': 0,
        'long_content': 0,
        'preserved_type': 0,
        'no_quality_score': 0
    }

    for memory in all_memories:
        metadata = memory.metadata or {}
        quality_score = metadata.get('quality_score')
        quality_provider = metadata.get('quality_provider')

        # Only process DeBERTa-scored memories
        if quality_provider != 'onnx_deberta':
            preserved['no_quality_score'] += 1
            continue

        # Skip if no quality score
        if quality_score is None:
            preserved['no_quality_score'] += 1
            continue

        # Preserve high quality
        if quality_score >= QUALITY_THRESHOLD:
            preserved['high_quality'] += 1
            continue

        # Preserve longer content (might be valuable despite low score)
        if len(memory.content) > MIN_LENGTH_EXCEPTION:
            preserved['long_content'] += 1
            continue

        # Preserve specific types
        if memory.memory_type in PRESERVE_TYPES:
            preserved['preserved_type'] += 1
            continue

        # Mark for deletion
        candidates.append({
            'hash': memory.content_hash,
            'type': memory.memory_type or '(no type)',
            'score': quality_score,
            'length': len(memory.content),
            'preview': memory.content[:80].replace('\n', ' ')
        })

    # Report findings
    print("=" * 80)
    print("Analysis Results")
    print("=" * 80)
    print()
    print(f"Memories to DELETE: {len(candidates)}")
    print(f"  Quality score <{QUALITY_THRESHOLD}")
    print(f"  Length ≤{MIN_LENGTH_EXCEPTION} characters")
    print(f"  Not in preserved types: {PRESERVE_TYPES}")
    print()
    print("Memories to PRESERVE:")
    print(f"  High quality (≥{QUALITY_THRESHOLD}): {preserved['high_quality']}")
    print(f"  Long content (>{MIN_LENGTH_EXCEPTION} chars): {preserved['long_content']}")
    print(f"  Preserved types: {preserved['preserved_type']}")
    print(f"  No quality score: {preserved['no_quality_score']}")
    print()

    if len(candidates) == 0:
        print("✓ No memories to delete!")
        return

    # Show breakdown by type
    print("Deletion Breakdown by Type:")
    from collections import Counter
    type_counts = Counter(c['type'] for c in candidates)
    for mem_type, count in sorted(type_counts.items(), key=lambda x: -x[1])[:15]:
        avg_score = sum(c['score'] for c in candidates if c['type'] == mem_type) / count
        print(f"  {mem_type:25s}: {count:4d} memories (avg score: {avg_score:.3f})")
    print()

    # Show sample deletions
    print("Sample Deletions (10 random):")
    import random
    samples = random.sample(candidates, min(10, len(candidates)))
    for sample in samples:
        print(f"  Score: {sample['score']:.4f} | Len: {sample['length']:4d} | Type: {sample['type']}")
        print(f"    {sample['preview'][:100]}")
        print()

    if dry_run:
        print("=" * 80)
        print("DRY RUN COMPLETE - No changes made")
        print("=" * 80)
        print()
        print("To execute cleanup, run:")
        print(f"  python {__file__} --execute")
        return

    # Execute cleanup
    print("=" * 80)
    print("EXECUTING CLEANUP")
    print("=" * 80)
    print()

    # Create deletion log
    log_path = Path.home() / 'backups/mcp-memory-service' / f'cleanup-log-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt'
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, 'w') as log:
        log.write(f"Cleanup executed: {datetime.now()}\n")
        log.write(f"Threshold: quality_score < {QUALITY_THRESHOLD}\n")
        log.write(f"Max length: {MIN_LENGTH_EXCEPTION} characters\n")
        log.write(f"Total deleted: {len(candidates)}\n\n")

        deleted_count = 0
        error_count = 0

        for i, candidate in enumerate(candidates, 1):
            try:
                success, message = await storage.delete(candidate['hash'])
                if success:
                    deleted_count += 1
                else:
                    error_count += 1
                    log.write(f"ERROR: {candidate['hash']}\t{message}\n")

                # Log deletion
                log.write(f"{candidate['hash']}\t{candidate['score']:.4f}\t{candidate['length']}\t{candidate['type']}\n")

                if i % 100 == 0:
                    print(f"  Deleted: {deleted_count}/{len(candidates)}")

            except Exception as e:
                error_count += 1
                log.write(f"ERROR: {candidate['hash']}\t{str(e)}\n")
                print(f"  Error deleting {candidate['hash'][:16]}...: {e}")

    print()
    print("=" * 80)
    print("CLEANUP COMPLETE")
    print("=" * 80)
    print()
    print(f"✓ Deleted: {deleted_count} memories")
    if error_count > 0:
        print(f"⚠ Errors: {error_count}")
    print(f"📝 Log saved: {log_path}")
    print()

    # Verify final state
    remaining = await storage.get_all_memories()
    print(f"Database state:")
    print(f"  Total memories: {len(remaining)}")
    print(f"  Removed: {len(all_memories) - len(remaining)}")

if __name__ == "__main__":
    # Check for --execute flag
    dry_run = '--execute' not in sys.argv

    asyncio.run(cleanup_low_quality(dry_run=dry_run))
