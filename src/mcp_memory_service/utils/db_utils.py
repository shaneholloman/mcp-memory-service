"""Utilities for database validation and health checks."""
from typing import Dict, Any, Tuple
import logging
import os
import json
from datetime import datetime

logger = logging.getLogger(__name__)

async def validate_database(storage) -> Tuple[bool, str]:
    """Validate database health and configuration."""
    try:
        # Check if storage is properly initialized
        if storage is None:
            return False, "Storage is not initialized"
        
        # Use the new initialization check method if available
        if hasattr(storage, 'is_initialized'):
            if not storage.is_initialized():
                # Get detailed status for debugging
                if hasattr(storage, 'get_initialization_status'):
                    status = storage.get_initialization_status()
                    return False, f"Storage not fully initialized: {status}"
                else:
                    return False, "Storage initialization incomplete"
        
        # Legacy checks for backward compatibility
        if storage.collection is None:
            return False, "Collection is not initialized"
        
        if storage.embedding_function is None:
            return False, "Embedding function is not initialized"
        
        # Get collection count safely
        try:
            collection_count = storage.collection.count()
            if collection_count == 0:
                logger.info("Database is empty but accessible")
        except Exception as count_error:
            return False, f"Cannot access collection: {str(count_error)}"
        
        # Verify embedding function is working
        test_text = "Database validation test"
        try:
            embedding = storage.embedding_function([test_text])
            if not embedding or len(embedding) == 0:
                return False, "Embedding function is not working properly"
        except Exception as embed_error:
            return False, f"Embedding function error: {str(embed_error)}"
        
        # Test basic operations
        test_id = "test_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Test add
            storage.collection.add(
                documents=[test_text],
                metadatas=[{"test": True}],
                ids=[test_id]
            )
            
            # Test query
            query_result = storage.collection.query(
                query_texts=[test_text],
                n_results=1
            )
            if not query_result["ids"]:
                return False, "Query operation failed"
            
            # Clean up test data
            storage.collection.delete(ids=[test_id])
            
        except Exception as ops_error:
            return False, f"Database operations failed: {str(ops_error)}"
        
        return True, "Database validation successful"
    except Exception as e:
        logger.error(f"Database validation failed: {str(e)}")
        return False, f"Database validation failed: {str(e)}"

def get_database_stats(storage) -> Dict[str, Any]:
    """Get detailed database statistics with proper error handling."""
    try:
        # Check if storage is properly initialized
        if storage is None:
            return {
                "status": "error",
                "error": "Storage is not initialized"
            }
        
        if storage.collection is None:
            return {
                "status": "error", 
                "error": "Collection is not initialized"
            }
        
        # Get collection count safely
        try:
            count = storage.collection.count()
        except Exception as count_error:
            return {
                "status": "error",
                "error": f"Cannot get collection count: {str(count_error)}"
            }
        
        # Get collection info
        collection_info = {
            "total_memories": count,
            "embedding_function": storage.embedding_function.__class__.__name__ if storage.embedding_function else "None",
            "metadata": storage.collection.metadata if hasattr(storage.collection, 'metadata') else {}
        }
        
        # Get storage info
        storage_info = {
            "path": storage.path,
            "size_bytes": 0,
            "size_mb": 0.0
        }
        
        try:
            db_path = storage.path
            if os.path.exists(db_path):
                size = 0
                for root, dirs, files in os.walk(db_path):
                    size += sum(os.path.getsize(os.path.join(root, name)) for name in files)
                
                storage_info.update({
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2)
                })
        except Exception as size_error:
            logger.warning(f"Could not calculate storage size: {str(size_error)}")
        
        return {
            "collection": collection_info,
            "storage": storage_info,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

async def repair_database(storage) -> Tuple[bool, str]:
    """Attempt to repair database issues."""
    try:
        # Validate current state
        is_valid, message = await validate_database(storage)
        if is_valid:
            return True, "Database is already healthy"
        
        # Backup current embeddings and metadata
        try:
            existing_data = storage.collection.get()
        except Exception as backup_error:
            logger.error(f"Could not backup existing data: {str(backup_error)}")
            existing_data = None
        
        # Recreate collection
        storage.client.delete_collection("memory_collection")
        storage.collection = storage.client.create_collection(
            name="memory_collection",
            metadata={"hnsw:space": "cosine"},
            embedding_function=storage.embedding_function
        )
        
        # Restore data if backup was successful
        if existing_data and existing_data["ids"]:
            storage.collection.add(
                documents=existing_data["documents"],
                metadatas=existing_data["metadatas"],
                ids=existing_data["ids"]
            )
        
        # Validate repair
        is_valid, message = await validate_database(storage)
        if is_valid:
            return True, "Database successfully repaired"
        else:
            return False, f"Repair failed: {message}"
            
    except Exception as e:
        logger.error(f"Error repairing database: {str(e)}")
        return False, f"Error repairing database: {str(e)}"