#!/usr/bin/env python3
"""
Migration script to update timestamp format in memory database.
This script reads all memories, updates timestamps to the new format, and saves them back.
"""
import sys
import os
import json
import asyncio
import logging
from pathlib import Path

# Add parent directory to path so we can import from the src directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_memory_service.storage.chroma import ChromaMemoryStorage
from src.mcp_memory_service.config import CHROMA_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("timestamp_migration")

async def migrate_timestamps():
    """
    Migrate all memories to use integer timestamps for consistent time-based queries.
    """
    logger.info(f"Initializing ChromaDB storage at {CHROMA_PATH}")
    storage = ChromaMemoryStorage(CHROMA_PATH)
    
    # Get all memories from the database
    logger.info("Retrieving all memories from database")
    try:
        # First try without embeddings to avoid potential issues
        results = storage.collection.get(
            include=["metadatas", "documents"]
        )
        
        if not results["ids"]:
            logger.info("No memories found in database")
            return
        
        total_memories = len(results["ids"])
        logger.info(f"Found {total_memories} memories")
        
        # Track which memories need to be updated
        memories_to_update = []
        
        # Check each memory's timestamp format
        for i, memory_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            document = results["documents"][i]
            
            # Extract current timestamp
            current_timestamp = metadata.get("timestamp")
            if not current_timestamp:
                logger.warning(f"Memory {memory_id} has no timestamp, skipping")
                continue
                
            logger.debug(f"Memory {i+1}/{total_memories}: ID={memory_id}, Current timestamp={current_timestamp}")
            
            # Convert timestamp to integer format
            try:
                # Handle different timestamp formats
                if isinstance(current_timestamp, (int, float)):
                    new_timestamp = int(float(current_timestamp))
                elif isinstance(current_timestamp, str):
                    if "." in current_timestamp:  # It's a float string
                        new_timestamp = int(float(current_timestamp))
                    else:
                        try:
                            # Make sure it's a valid integer
                            new_timestamp = int(current_timestamp)
                        except ValueError:
                            # Not a valid integer string, convert it
                            new_timestamp = int(float(current_timestamp))
                else:
                    logger.warning(f"Memory {memory_id} has unexpected timestamp type: {type(current_timestamp)}")
                    continue
                
                # Check if the timestamp needs to be updated
                if current_timestamp != new_timestamp:
                    logger.info(f"Memory {memory_id}: Changing timestamp from {current_timestamp} to {new_timestamp}")
                    
                    # Update the metadata with the new timestamp
                    new_metadata = metadata.copy()
                    new_metadata["timestamp"] = new_timestamp
                    
                    memories_to_update.append({
                        "id": memory_id,
                        "document": document,
                        "metadata": new_metadata
                    })
            except Exception as e:
                logger.error(f"Error processing memory {memory_id}: {str(e)}")
                continue
        
        # Update the memories in the database
        if memories_to_update:
            update_count = len(memories_to_update)
            logger.info(f"Updating {update_count} memories with new timestamp format")
            
            # Process in batches to avoid overwhelming the database
            batch_size = 50
            for i in range(0, len(memories_to_update), batch_size):
                batch = memories_to_update[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(memories_to_update)-1)//batch_size + 1}")
                
                # Prepare batch arrays for update
                batch_ids = []
                batch_metadatas = []
                batch_documents = []
                
                for memory in batch:
                    batch_ids.append(memory["id"])
                    batch_metadatas.append(memory["metadata"])
                    batch_documents.append(memory["document"])
                
                try:
                    # Update the entire batch at once
                    storage.collection.update(
                        ids=batch_ids,
                        metadatas=batch_metadatas,
                        documents=batch_documents
                    )
                except Exception as e:
                    logger.error(f"Error updating batch: {str(e)}")
            
            logger.info(f"Successfully updated {update_count} memories")
        else:
            logger.info("No memories need timestamp format updates")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

async def verify_migration():
    """
    Verify that the migration was successful by checking timestamp formats.
    """
    logger.info("Verifying migration results")
    storage = ChromaMemoryStorage(CHROMA_PATH)
    
    try:
        results = storage.collection.get(
            include=["metadatas"]
        )
        
        if not results["ids"]:
            logger.info("No memories found in database")
            return
        
        total_memories = len(results["ids"])
        invalid_count = 0
        
        for i, memory_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            timestamp = metadata.get("timestamp")
            
            if not timestamp:
                logger.warning(f"Memory {memory_id} has no timestamp")
                invalid_count += 1
                continue
                
            # Check if timestamp is an integer
            if not isinstance(timestamp, int):
                try:
                    # Try to convert to make sure it can be represented as an integer
                    int(timestamp)
                except (ValueError, TypeError):
                    logger.warning(f"Memory {memory_id} has invalid timestamp format: {timestamp}")
                    invalid_count += 1
        
        if invalid_count == 0:
            logger.info(f"Verification successful: All {total_memories} memories have valid timestamp format")
        else:
            logger.warning(f"Verification found {invalid_count} out of {total_memories} memories with invalid timestamp format")
            
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        raise
        
async def test_time_query():
    """
    Test time-based memory queries to ensure they're working correctly.
    """
    logger.info("Testing time-based memory queries")
    storage = ChromaMemoryStorage(CHROMA_PATH)
    
    try:
        # Try querying memories from the past week
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        
        logger.info(f"Testing query for past week: {start_date} to {end_date}")
        logger.info(f"Timestamp range: {start_timestamp} to {end_timestamp}")
        
        # Build time filtering where clause
        where_clause = {
            "$and": [
                {"timestamp": {"$gte": int(start_timestamp)}},
                {"timestamp": {"$lte": int(end_timestamp)}}
            ]
        }
        
        # Direct query using where clause
        results = storage.collection.get(
            where=where_clause,
            include=["metadatas", "documents"]
        )
        
        if not results["ids"]:
            logger.info("No memories found in the past week")
        else:
            logger.info(f"Found {len(results['ids'])} memories in the past week")
            
            # Log the first few memories
            for i, memory_id in enumerate(results["ids"][:3]):
                metadata = results["metadatas"][i]
                document = results["documents"][i]
                logger.info(f"Memory {i+1}: ID={memory_id}, Timestamp={metadata.get('timestamp')}, Content={document[:50]}...")
    
    except Exception as e:
        logger.error(f"Error during time query test: {str(e)}")
        raise

async def main():
    """Main function to run the migration."""
    logger.info("=== Starting timestamp migration ===")
    
    try:
        # Run migration
        await migrate_timestamps()
        
        # Verify migration
        await verify_migration()
        
        # Test time query
        await test_time_query()
        
        logger.info("=== Migration completed successfully ===")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())