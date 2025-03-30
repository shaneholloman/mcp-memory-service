# scripts/repair_memories.py

import asyncio
import json
import logging
from mcp_memory_service.storage.chroma import ChromaMemoryStorage
from mcp_memory_service.utils.hashing import generate_content_hash
import argparse

logger = logging.getLogger(__name__)

async def repair_missing_hashes(storage):
    """Repair memories missing content_hash by generating new ones"""
    results = storage.collection.get(
        include=["metadatas", "documents"]
    )
    
    fixed_count = 0
    for i, meta in enumerate(results["metadatas"]):
        memory_id = results["ids"][i]
        
        if "content_hash" not in meta:
            try:
                # Generate hash from content and metadata
                content = results["documents"][i]
                # Create a copy of metadata without the content_hash field
                meta_for_hash = {k: v for k, v in meta.items() if k != "content_hash"}
                new_hash = generate_content_hash(content, meta_for_hash)
                
                # Update metadata with new hash
                new_meta = meta.copy()
                new_meta["content_hash"] = new_hash
                
                # Update the memory
                storage.collection.update(
                    ids=[memory_id],
                    metadatas=[new_meta]
                )
                
                logger.info(f"Fixed memory {memory_id} with new hash: {new_hash}")
                fixed_count += 1
                
            except Exception as e:
                logger.error(f"Error fixing memory {memory_id}: {str(e)}")
    
    return fixed_count

async def main():
log_level = os.getenv('LOG_LEVEL', 'ERROR').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.ERROR),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
    
    parser = argparse.ArgumentParser(description='Repair memories with missing content hashes')
    parser.add_argument('--db-path', required=True, help='Path to ChromaDB database')
    args = parser.parse_args()
    
    logger.info(f"Connecting to database at: {args.db_path}")
    storage = ChromaMemoryStorage(args.db_path)
    
    logger.info("Starting repair process...")
    fixed_count = await repair_missing_hashes(storage)
    logger.info(f"Repair completed. Fixed {fixed_count} memories")
    
    # Run validation again to confirm fixes
    logger.info("Running validation to confirm fixes...")
    from validate_memories import run_validation_report
    report = await run_validation_report(storage)
    print("\nPost-repair validation report:")
    print(report)

if __name__ == "__main__":
    asyncio.run(main())