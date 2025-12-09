#!/usr/bin/env python3
"""Re-score all DeBERTa memories with corrected model."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Use SQLite directly to avoid Cloudflare network timeouts
from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.config import SQLITE_VEC_PATH
from mcp_memory_service.quality.onnx_ranker import get_onnx_ranker_model

async def rescore():
    print("Loading DeBERTa...")
    deberta = get_onnx_ranker_model('nvidia-quality-classifier-deberta', 'auto')

    print("Connecting to storage (SQLite-vec only, no network)...")
    storage = SqliteVecMemoryStorage(SQLITE_VEC_PATH)
    await storage.initialize()

    print("Fetching memories...")
    all_memories = await storage.get_all_memories()

    to_rescore = [m for m in all_memories
                  if m.metadata and m.metadata.get('quality_provider') == 'onnx_deberta']

    print(f"Re-scoring {len(to_rescore)} memories...")

    for i, m in enumerate(to_rescore, 1):
        new_score = deberta.score_quality("", m.content)
        await storage.update_memory_metadata(
            content_hash=m.content_hash,
            updates={'quality_score': new_score}
        )
        if i % 100 == 0:
            print(f"  [{i:5d}/{len(to_rescore)}] Score: {new_score:.3f}")

    print(f"\n✓ Re-scored {len(to_rescore)} memories")
    print("Note: Changes saved to SQLite. Hybrid backend will sync to Cloudflare automatically.")

if __name__ == "__main__":
    asyncio.run(rescore())
