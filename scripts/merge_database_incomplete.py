#!/usr/bin/env python3
"""
ChromaDB Database Merging Script - Evolved from Timestamp Migration

This script serves as a prototype for comprehensive database merging capabilities
in the MCP Memory Service.

Proposed Feature: Database Merging System
--------------------------------------------
Objectives:
- Support multiple database merging strategies
- Enable distributed database operations
- Provide robust data migration tools

Planned Merging Strategies:
1. Sequential Import/Export Method
   - Safest approach for moderate-sized databases
   - Handles duplicate detection
   - Preserves collection metadata

2. Direct File System Merging
   - High-performance for large databases
   - Requires careful connection management

3. Create New Merged Database
   - Safest option for conflict resolution
   - Allows data transformation

Proposed New Tools:
- merge_databases(): Primary merging method
- check_database_compatibility(): Validate database compatibility


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
from datetime import datetime, timedelta, timezone

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
            
            # Check how timestamp is stored
            current_timestamp = None
            
            # First check embedding_metadata int_value
            try:
                # Get raw timestamp from embedding_metadata
                raw_results = storage.client.raw_sql(
                    "SELECT int_value FROM embedding_metadata WHERE id = ? AND key = 'timestamp'",
                    [memory_id]
                )
                if raw_results:
                    current_timestamp = raw_results[0][0]
                    logger.debug(f"Found timestamp in int_value: {current_timestamp}")
            except Exception as e:
                logger.debug(f"Could not query embedding_metadata: {str(e)}")
            
            # Check both storage locations
            metadata_timestamp = metadata.get("timestamp")
            int_value_timestamp = None
            
            if current_timestamp is not None:
                int_value_timestamp = current_timestamp
            
            # If we have a timestamp in either location, use it
            if int_value_timestamp is not None:
                current_timestamp = int_value_timestamp
                logger.debug(f"Using int_value timestamp: {current_timestamp}")
            elif metadata_timestamp is not None:
                current_timestamp = metadata_timestamp
                logger.debug(f"Using metadata timestamp: {current_timestamp}")
            else:
                logger.warning(f"Memory {memory_id} has no timestamp in either location, skipping")
                continue
                
            logger.debug(f"Memory {i+1}/{total_memories}: ID={memory_id}, Current timestamp={current_timestamp}")
            logger.debug(f"  Int_value timestamp: {int_value_timestamp}")
            logger.debug(f"  Metadata timestamp: {metadata_timestamp}")
            
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
                
                # Ensure timestamp is stored in embedding_metadata int_value
                try:
                    # Start transaction
                    storage.client.raw_sql("BEGIN TRANSACTION", [])
                    
                    try:
                        # First clear any existing timestamp values
                        storage.client.raw_sql(
                            """
                            DELETE FROM embedding_metadata 
                            WHERE id = ? AND key = 'timestamp'
                            """,
                            [memory_id]
                        )
                        
                        # Then insert the new timestamp as int_value
                        storage.client.raw_sql(
                            """
                            INSERT INTO embedding_metadata (id, key, int_value)
                            VALUES (?, 'timestamp', ?)
                            """,
                            [memory_id, new_timestamp]
                        )
                        
                        # Verify the timestamp was stored correctly
                        verify_result = storage.client.raw_sql(
                            """
                            SELECT int_value 
                            FROM embedding_metadata 
                            WHERE id = ? AND key = 'timestamp'
                            """,
                            [memory_id]
                        )
                        
                        if not verify_result or verify_result[0][0] != new_timestamp:
                            raise Exception(f"Verification failed: stored value {verify_result[0][0] if verify_result else 'None'} != {new_timestamp}")
                            
                        # Commit transaction if everything succeeded
                        storage.client.raw_sql("COMMIT", [])
                        logger.debug(f"Updated and verified int_value timestamp for memory {memory_id}")
                    except Exception as inner_e:
                        # Rollback on any error
                        storage.client.raw_sql("ROLLBACK", [])
                        raise inner_e
                except Exception as e:
                    logger.error(f"Failed to update int_value timestamp for memory {memory_id}: {str(e)}")
                
                # Always ensure metadata matches int_value
                if metadata.get("timestamp") != new_timestamp:
                    logger.info(f"Memory {memory_id}: Updating metadata timestamp to match int_value")
                    logger.info(f"  Old value: {metadata.get('timestamp')}")
                    logger.info(f"  New value: {new_timestamp}")
                    
                    # Update the metadata with the new timestamp
                    new_metadata = metadata.copy()
                    new_metadata["timestamp"] = new_timestamp
                    
                    memories_to_update.append({
                        "id": memory_id,
                        "document": document,
                        "metadata": new_metadata
                    })
                else:
                    logger.debug(f"Memory {memory_id}: Metadata timestamp already matches int_value")
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
    Verify that the migration was successful by checking timestamp formats in both storage locations.
    """
    logger.info("Verifying migration results")
    storage = ChromaMemoryStorage(CHROMA_PATH)
    
    try:
        # Get all memories
        results = storage.collection.get(
            include=["metadatas"]
        )
        
        if not results["ids"]:
            logger.info("No memories found in database")
            return
        
        total_memories = len(results["ids"])
        logger.info(f"Checking {total_memories} memories...")
        
        # Track issues
        metadata_issues = []
        int_value_issues = []
        mismatch_issues = []
        
        for i, memory_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            
            # Check metadata timestamp
            metadata_timestamp = metadata.get("timestamp")
            if not metadata_timestamp:
                metadata_issues.append(f"Memory {memory_id} has no metadata timestamp")
                continue
            
            # Verify metadata timestamp is integer
            if not isinstance(metadata_timestamp, int):
                try:
                    metadata_timestamp = int(float(metadata_timestamp))
                except (ValueError, TypeError):
                    metadata_issues.append(f"Memory {memory_id} has invalid metadata timestamp format: {metadata_timestamp}")
                    continue
            
            # Check int_value timestamp
            try:
                raw_results = storage.client.raw_sql(
                    "SELECT int_value FROM embedding_metadata WHERE id = ? AND key = 'timestamp'",
                    [memory_id]
                )
                if not raw_results:
                    int_value_issues.append(f"Memory {memory_id} has no int_value timestamp")
                    continue
                    
                int_value_timestamp = raw_results[0][0]
                
                # Compare timestamps
                if int_value_timestamp != metadata_timestamp:
                    mismatch_issues.append(
                        f"Memory {memory_id} has mismatched timestamps: "
                        f"metadata={metadata_timestamp} ({datetime.fromtimestamp(metadata_timestamp)}), "
                        f"int_value={int_value_timestamp} ({datetime.fromtimestamp(int_value_timestamp)})"
                    )
            except Exception as e:
                int_value_issues.append(f"Memory {memory_id} error checking int_value: {str(e)}")
        
        # Report results
        success = True
        if metadata_issues:
            success = False
            logger.warning("Metadata timestamp issues:")
            for issue in metadata_issues[:5]:  # Show first 5 issues
                logger.warning(f"  {issue}")
            if len(metadata_issues) > 5:
                logger.warning(f"  ...and {len(metadata_issues) - 5} more issues")
                
        if int_value_issues:
            success = False
            logger.warning("Int_value timestamp issues:")
            for issue in int_value_issues[:5]:
                logger.warning(f"  {issue}")
            if len(int_value_issues) > 5:
                logger.warning(f"  ...and {len(int_value_issues) - 5} more issues")
                
        if mismatch_issues:
            success = False
            logger.warning("Timestamp mismatch issues:")
            for issue in mismatch_issues[:5]:
                logger.warning(f"  {issue}")
            if len(mismatch_issues) > 5:
                logger.warning(f"  ...and {len(mismatch_issues) - 5} more issues")
        
        if success:
            logger.info(f"Verification successful: All {total_memories} memories have valid timestamps in both locations")
        else:
            total_issues = len(metadata_issues) + len(int_value_issues) + len(mismatch_issues)
            logger.warning(f"Verification found {total_issues} issues across {total_memories} memories")
            
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
        # Use dynamic time range (past week) with UTC timestamps
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        start_timestamp = int(start_date.timestamp())  # Earlier time = smaller timestamp
        end_timestamp = int(end_date.timestamp())      # Later time = larger timestamp
        
        # For logging, convert to local time
        local_tz = datetime.now().astimezone().tzinfo
        local_start = start_date.astimezone(local_tz)
        local_end = end_date.astimezone(local_tz)
        
        logger.info(f"Testing query for past week:")
        logger.info(f"UTC: {start_date} to {end_date}")
        logger.info(f"Local: {local_start} to {local_end}")
        logger.info(f"Timestamp range: {start_timestamp} to {end_timestamp}")
        
        # Get all memories first
        all_memories = {}  # id -> {timestamp, document}
        
        # Check int_value storage
        try:
            raw_results = storage.client.raw_sql(
                """
                SELECT m.id, m.int_value, e.document
                FROM embedding_metadata m
                JOIN embeddings e ON m.id = e.id
                WHERE m.key = 'timestamp'
                """,
                []
            )
            
            if raw_results:
                logger.info(f"Found {len(raw_results)} memories in int_value storage")
                for row in raw_results:
                    memory_id, timestamp, document = row
                    if start_timestamp <= timestamp <= end_timestamp:
                        all_memories[memory_id] = {
                            "timestamp": timestamp,
                            "document": document,
                            "source": "int_value"
                        }
        except Exception as e:
            logger.error(f"Error querying int_value storage: {str(e)}")
        
        # Check metadata storage using ChromaDB's where clause
        try:
            # Build time filtering where clause for ChromaDB
            where_clause = {
                "$and": [
                    {"timestamp": {"$gte": start_timestamp}},  # Use raw timestamps, ChromaDB handles conversion
                    {"timestamp": {"$lte": end_timestamp}}
                ]
            }
            
            # Query with time range filter
            results = storage.collection.get(
                where=where_clause,
                include=["metadatas", "documents"]
            )
            
            if results["ids"]:
                logger.info(f"Found {len(results['ids'])} total memories in metadata storage")
                for i, memory_id in enumerate(results["ids"]):
                    metadata = results["metadatas"][i]
                    timestamp = metadata.get("timestamp")
                    # ChromaDB where clause already filtered by timestamp range
                    # Only add if not already found in int_value or if int_value timestamp differs
                    existing = all_memories.get(memory_id)
                    if not existing or existing["timestamp"] != timestamp:
                        all_memories[memory_id] = {
                            "timestamp": timestamp,
                            "document": results["documents"][i],
                            "source": "metadata"
                        }
        except Exception as e:
            logger.error(f"Error querying metadata storage: {str(e)}")
        
        # Report findings
        if all_memories:
            logger.info(f"Found {len(all_memories)} total memories in the time range")
            logger.info("Sample of found memories:")
            for memory_id, data in list(all_memories.items())[:3]:
                logger.info(
                    f"Memory {memory_id} (from {data['source']}): "
                    f"Timestamp={data['timestamp']} "
                    f"({datetime.fromtimestamp(data['timestamp'])}), "
                    f"Content={data['document'][:50]}..."
                )
        else:
            logger.warning("No memories found in either storage for this time range")
            
        # If no memories found, show sample of actual data
        if not all_memories:
            logger.info("Checking sample of actual data:")
            try:
                # Sample from int_value storage
                sample_raw = storage.client.raw_sql(
                    """
                    SELECT m.id, m.int_value, e.document 
                    FROM embedding_metadata m
                    JOIN embeddings e ON m.id = e.id
                    WHERE m.key = 'timestamp'
                    ORDER BY m.int_value DESC
                    LIMIT 3
                    """
                )
                if sample_raw:
                    logger.info("Sample from int_value storage (most recent first):")
                    for row in sample_raw:
                        memory_id, timestamp, document = row
                        logger.info(
                            f"ID: {memory_id}, "
                            f"Timestamp: {timestamp} ({datetime.fromtimestamp(timestamp)}), "
                            f"Content: {document[:50]}..."
                        )
                
                # Sample from metadata storage
                sample_meta = storage.collection.get(
                    limit=3,
                    include=["metadatas", "documents"]
                )
                if sample_meta["ids"]:
                    logger.info("Sample from metadata storage:")
                    for i, metadata in enumerate(sample_meta["metadatas"]):
                        ts = metadata.get("timestamp")
                        if ts:
                            logger.info(
                                f"ID: {sample_meta['ids'][i]}, "
                                f"Timestamp: {ts} ({datetime.fromtimestamp(ts)}), "
                                f"Content: {sample_meta['documents'][i][:50]}..."
                            )
            except Exception as e:
                logger.error(f"Error getting data samples: {str(e)}")
    
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
