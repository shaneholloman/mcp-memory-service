#!/usr/bin/env python3
"""
Migrate existing quality scores from MS-MARCO to DeBERTa.

This script re-evaluates all memories with the NVIDIA DeBERTa quality classifier,
replacing scores from the MS-MARCO cross-encoder with absolute quality assessments.

Usage:
    python scripts/quality/migrate_to_deberta.py

The script will:
1. Load all memories scored with MS-MARCO (quality_provider='onnx_local')
2. Re-evaluate using DeBERTa classifier (absolute quality)
3. Compare score distributions (before/after)
4. Update metadata with new scores and migration history
"""

import asyncio
import sys
from pathlib import Path
import logging

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_memory_service.storage.factory import create_storage_instance
from mcp_memory_service.config import STORAGE_BACKEND, SQLITE_VEC_PATH
from mcp_memory_service.quality.onnx_ranker import get_onnx_ranker_model

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_quality_scores():
    """
    Re-evaluate all memories with DeBERTa model.

    Process:
    1. Load all memories with MS-MARCO scores (quality_provider='onnx_local')
    2. Re-evaluate using DeBERTa classifier
    3. Compare score distributions
    4. Update with new scores (preserving access patterns)
    """

    print("=" * 80)
    print("Quality Score Migration: MS-MARCO → DeBERTa")
    print("=" * 80)
    print()

    # Initialize DeBERTa model
    print("📥 Loading DeBERTa model...")
    deberta = get_onnx_ranker_model(
        model_name='nvidia-quality-classifier-deberta',
        device='auto'
    )

    if deberta is None:
        print("❌ Failed to load DeBERTa model")
        print("   Make sure to export it first:")
        print("   python scripts/quality/export_deberta_onnx.py")
        return 1

    print(f"✓ DeBERTa loaded: {deberta.model_config['hf_name']}")
    print(f"  Device: {deberta._model.get_providers()[0]}")
    print()

    # Create storage instance
    print("📂 Connecting to storage...")
    storage = await create_storage_instance(SQLITE_VEC_PATH, server_type="script")
    print(f"✓ Connected to {STORAGE_BACKEND} backend")
    print()

    try:
        # Pause sync if hybrid
        if STORAGE_BACKEND == 'hybrid' and hasattr(storage, 'pause_sync'):
            print("⏸️  Pausing hybrid sync...")
            await storage.pause_sync()
            print("✓ Sync paused for migration")
            print()

        # Get all memories
        print("📊 Fetching memories...")
        all_memories = await storage.get_all_memories()
        print(f"✓ Found {len(all_memories)} total memories")
        print()

        # Filter: MS-MARCO scored, non-system memories
        to_migrate = []
        for m in all_memories:
            metadata = m.metadata or {}
            provider = metadata.get('quality_provider', '')

            # Skip system-generated memories
            if m.memory_type in ['association', 'compressed_cluster']:
                continue

            # Migrate memories with onnx_local provider (MS-MARCO)
            if provider == 'onnx_local':
                to_migrate.append(m)

        print(f"🎯 Memories to migrate: {len(to_migrate)}")
        if len(to_migrate) == 0:
            print("   No memories with MS-MARCO scores found.")
            print("   All memories may already use DeBERTa or have no quality scores.")
            return 0

        print()

        # Statistics tracking
        old_scores = []
        new_scores = []
        changes = []

        print("🔄 Re-evaluating with DeBERTa...")
        print()

        for i, memory in enumerate(to_migrate, 1):
            try:
                old_score = memory.metadata.get('quality_score', 0.5)
                old_scores.append(old_score)

                # DeBERTa: Absolute quality (no query needed)
                new_score = deberta.score_quality("", memory.content)
                new_scores.append(new_score)

                score_delta = new_score - old_score
                changes.append(score_delta)

                # Update metadata
                await storage.update_memory_metadata(
                    content_hash=memory.content_hash,
                    updates={
                        'quality_score': new_score,
                        'quality_provider': 'onnx_deberta',  # New provider tag
                        'quality_migration': {
                            'from_model': 'ms-marco-MiniLM-L-6-v2',
                            'from_score': old_score,
                            'to_model': 'nvidia-quality-classifier-deberta',
                            'to_score': new_score,
                            'score_delta': score_delta
                        }
                    },
                    preserve_timestamps=True
                )

                # Progress indicator
                if i % 100 == 0 or i == len(to_migrate):
                    avg_new = sum(new_scores) / len(new_scores)
                    print(f"  [{i:5d}/{len(to_migrate)}] Current avg: {avg_new:.3f}")

            except Exception as e:
                logger.error(f"Error migrating {memory.content_hash[:16]}: {e}")

        print()
        print("=" * 80)
        print("✅ Migration Complete!")
        print("=" * 80)
        print()

        # Statistics
        import numpy as np

        def get_quality_tiers(scores):
            """Calculate quality tier distribution."""
            high = sum(1 for s in scores if s >= 0.7)
            medium = sum(1 for s in scores if 0.5 <= s < 0.7)
            low = sum(1 for s in scores if s < 0.5)
            return high, medium, low

        print("📈 Score Distribution Comparison:")
        print()

        # MS-MARCO (old) stats
        old_high, old_medium, old_low = get_quality_tiers(old_scores)
        print(f"MS-MARCO (before):")
        print(f"  Mean:   {np.mean(old_scores):.3f}")
        print(f"  Std:    {np.std(old_scores):.3f}")
        print(f"  Median: {np.median(old_scores):.3f}")
        print(f"  High (≥0.7):    {old_high:5d} ({old_high/len(old_scores)*100:5.1f}%)")
        print(f"  Medium (0.5-0.7): {old_medium:5d} ({old_medium/len(old_scores)*100:5.1f}%)")
        print(f"  Low (<0.5):      {old_low:5d} ({old_low/len(old_scores)*100:5.1f}%)")
        print()

        # DeBERTa (new) stats
        new_high, new_medium, new_low = get_quality_tiers(new_scores)
        print(f"DeBERTa (after):")
        print(f"  Mean:   {np.mean(new_scores):.3f}")
        print(f"  Std:    {np.std(new_scores):.3f}")
        print(f"  Median: {np.median(new_scores):.3f}")
        print(f"  High (≥0.7):    {new_high:5d} ({new_high/len(new_scores)*100:5.1f}%)")
        print(f"  Medium (0.5-0.7): {new_medium:5d} ({new_medium/len(new_scores)*100:5.1f}%)")
        print(f"  Low (<0.5):      {new_low:5d} ({new_low/len(new_scores)*100:5.1f}%)")
        print()

        # Changes analysis
        print(f"Score Changes:")
        print(f"  Mean delta:      {np.mean(changes):+.3f}")
        print(f"  Std delta:       {np.std(changes):.3f}")
        print(f"  Increased (>+0.1): {sum(1 for d in changes if d > 0.1):5d} memories")
        print(f"  Decreased (<-0.1): {sum(1 for d in changes if d < -0.1):5d} memories")
        print(f"  Stable (±0.1):   {sum(1 for d in changes if abs(d) <= 0.1):5d} memories")
        print()

        # Expected improvements
        mean_improvement = np.mean(new_scores) - np.mean(old_scores)
        perfect_scores_old = sum(1 for s in old_scores if s > 0.99)
        perfect_scores_new = sum(1 for s in new_scores if s > 0.99)

        print("🎯 Key Metrics:")
        print(f"  Mean improvement:      {mean_improvement:+.3f}")
        print(f"  Perfect 1.0 scores:    {perfect_scores_old} → {perfect_scores_new} ({perfect_scores_old - perfect_scores_new:+d})")
        print(f"  High quality increase: {old_high} → {new_high} ({new_high - old_high:+d})")
        print()

        if mean_improvement > 0.05:
            print("✅ Significant improvement in average quality scores")
        elif mean_improvement > 0:
            print("✓ Modest improvement in average quality scores")
        else:
            print("⚠️ Average scores decreased (may indicate more accurate assessment)")

        if perfect_scores_new < perfect_scores_old:
            reduction = (1 - perfect_scores_new / max(perfect_scores_old, 1)) * 100
            print(f"✅ Reduced false positives: {reduction:.0f}% fewer perfect scores")

    finally:
        # Resume sync
        if STORAGE_BACKEND == 'hybrid' and hasattr(storage, 'resume_sync'):
            print()
            print("▶️  Resuming hybrid sync...")
            await storage.resume_sync()
            print("✓ Sync resumed")

            # Wait for sync queue to drain
            if hasattr(storage, 'wait_for_sync_completion'):
                print()
                print("⏳ Waiting for sync to complete...")
                try:
                    stats = await storage.wait_for_sync_completion(timeout=600)
                    print("✓ Sync completed successfully")
                    print(f"   Synced: {stats['success_count']} operations")
                    if stats['failure_count'] > 0:
                        print(f"   ⚠️ Failed: {stats['failure_count']} operations (will retry)")
                except TimeoutError as e:
                    print(f"⚠️ {e}")
                    print("   Background sync will continue")

        await storage.close()

        print()
        print("💡 Next Steps:")
        print("   1. Verify results:")
        print("      curl -ks https://127.0.0.1:8000/api/quality/distribution | python3 -m json.tool")
        print()
        print("   2. Update environment to use DeBERTa by default:")
        print("      echo 'export MCP_QUALITY_LOCAL_MODEL=nvidia-quality-classifier-deberta' >> .env")
        print()
        print("   3. Restart MCP services:")
        print("      systemctl --user restart mcp-memory-http.service")
        print("      # In Claude Code: /mcp")

    return 0


if __name__ == '__main__':
    exit_code = asyncio.run(migrate_quality_scores())
    sys.exit(exit_code)
