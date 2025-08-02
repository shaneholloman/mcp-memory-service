# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for database validation and health checks."""
from typing import Dict, Any, Tuple
import logging
import os
import json
from datetime import datetime
import importlib

logger = logging.getLogger(__name__)

async def validate_database(storage) -> Tuple[bool, str]:
    """Validate database health and configuration."""
    try:
        # Check if storage is properly initialized
        if storage is None:
            return False, "Storage is not initialized"
        
        # Special case for direct access without checking for attribute 'collection'
        # This fixes compatibility issues with both ChromaDB and SQLite-vec backends
        storage_type = storage.__class__.__name__
        
        # First, use the 'is_initialized' method if available (preferred)
        if hasattr(storage, 'is_initialized') and callable(storage.is_initialized):
            try:
                init_status = storage.is_initialized()
                if not init_status:
                    # Get detailed status for debugging
                    if hasattr(storage, 'get_initialization_status') and callable(storage.get_initialization_status):
                        status = storage.get_initialization_status()
                        return False, f"Storage not fully initialized: {status}"
                    else:
                        return False, "Storage initialization incomplete"
            except Exception as init_error:
                logger.warning(f"Error checking initialization status: {init_error}")
                # Continue with alternative checks
        
        # SQLite-vec backend validation
        if storage_type == "SqliteVecMemoryStorage":
            if not hasattr(storage, 'conn') or storage.conn is None:
                return False, "SQLite database connection is not initialized"
            
            # Check for database health
            try:
                # Make sure the tables exist
                try:
                    cursor = storage.conn.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="memories"')
                    if not cursor.fetchone():
                        return False, "SQLite database is missing required tables"
                except Exception as table_error:
                    return False, f"Failed to check for tables: {str(table_error)}"
                
                # Try a simple query to verify database connection
                cursor = storage.conn.execute('SELECT COUNT(*) FROM memories')
                memory_count = cursor.fetchone()[0]
                logger.info(f"SQLite-vec database contains {memory_count} memories")
                
                # Test if embedding generation works (if model is available)
                if hasattr(storage, 'embedding_model') and storage.embedding_model:
                    test_text = "Database validation test"
                    embedding = storage._generate_embedding(test_text)
                    if not embedding or len(embedding) != storage.embedding_dimension:
                        logger.warning("Embedding generation may not be working properly")
                else:
                    logger.warning("No embedding model available, some functionality may be limited")
                
                return True, "SQLite-vec database validation successful"
                
            except Exception as e:
                return False, f"SQLite database access error: {str(e)}"
        
        # ChromaDB backend validation
        elif hasattr(storage, 'collection'):
            if storage.collection is None:
                return False, "Collection is not initialized"
            
            if hasattr(storage, 'embedding_function') and storage.embedding_function is None:
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
            
            return True, "ChromaDB validation successful"
        else:
            return False, f"Unknown storage type: {storage_type}"
            
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
        
        # Determine storage type
        storage_type = storage.__class__.__name__
        
        # SQLite-vec backend stats
        if storage_type == "SqliteVecMemoryStorage":
            # Use the storage's own stats method if available
            if hasattr(storage, 'get_stats') and callable(storage.get_stats):
                try:
                    stats = storage.get_stats()
                    stats["status"] = "healthy"
                    return stats
                except Exception as stats_error:
                    logger.warning(f"Error calling get_stats method: {stats_error}")
                    # Fall back to our implementation
            
            # Otherwise, gather basic stats
            if not hasattr(storage, 'conn') or storage.conn is None:
                return {
                    "status": "error",
                    "error": "SQLite database connection is not initialized"
                }
            
            try:
                # Check if tables exist
                cursor = storage.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Count memories if the table exists
                memory_count = 0
                if 'memories' in tables:
                    cursor = storage.conn.execute('SELECT COUNT(*) FROM memories')
                    memory_count = cursor.fetchone()[0]
                
                # Get unique tags if the table exists
                unique_tags = 0
                if 'memories' in tables:
                    cursor = storage.conn.execute('SELECT COUNT(DISTINCT tags) FROM memories WHERE tags != ""')
                    unique_tags = cursor.fetchone()[0]
                
                # Get database file size
                db_path = storage.db_path if hasattr(storage, 'db_path') else "unknown"
                file_size = os.path.getsize(db_path) if isinstance(db_path, str) and os.path.exists(db_path) else 0
                
                # Get embedding model info
                embedding_model = "unknown"
                embedding_dimension = 0
                
                if hasattr(storage, 'embedding_model_name'):
                    embedding_model = storage.embedding_model_name
                
                if hasattr(storage, 'embedding_dimension'):
                    embedding_dimension = storage.embedding_dimension
                
                # Gather tables information
                tables_info = {}
                for table in tables:
                    try:
                        cursor = storage.conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        tables_info[table] = {"count": count}
                    except Exception:
                        tables_info[table] = {"count": "unknown"}
                
                return {
                    "backend": "sqlite-vec",
                    "status": "healthy",
                    "total_memories": memory_count,
                    "unique_tags": unique_tags,
                    "database_size_bytes": file_size,
                    "database_size_mb": round(file_size / (1024 * 1024), 2) if file_size > 0 else 0,
                    "embedding_model": embedding_model,
                    "embedding_dimension": embedding_dimension,
                    "tables": tables,
                    "tables_info": tables_info
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error getting SQLite-vec stats: {str(e)}"
                }
        
        # ChromaDB backend stats
        elif hasattr(storage, 'collection'):
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
                "path": storage.path if hasattr(storage, 'path') else "unknown",
                "size_bytes": 0,
                "size_mb": 0.0
            }
            
            try:
                if hasattr(storage, 'path'):
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
                "backend": "chromadb",
                "status": "healthy"
            }
        else:
            return {
                "status": "error",
                "error": f"Unknown storage type: {storage_type}"
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
        # Determine storage type
        storage_type = storage.__class__.__name__
        
        # SQLite-vec backend repair
        if storage_type == "SqliteVecMemoryStorage":
            # For SQLite, we'll try to check and recreate the tables if needed
            if not hasattr(storage, 'conn') or storage.conn is None:
                # Try to reconnect
                try:
                    storage.conn = storage.conn or __import__('sqlite3').connect(storage.db_path)
                    
                    # Try to reload the extension
                    if importlib.util.find_spec('sqlite_vec'):
                        import sqlite_vec
                        storage.conn.enable_load_extension(True)
                        sqlite_vec.load(storage.conn)
                        storage.conn.enable_load_extension(False)
                    
                    # Recreate tables if needed
                    storage.conn.execute('''
                        CREATE TABLE IF NOT EXISTS memories (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            content_hash TEXT UNIQUE NOT NULL,
                            content TEXT NOT NULL,
                            tags TEXT,
                            memory_type TEXT,
                            metadata TEXT,
                            created_at REAL,
                            updated_at REAL,
                            created_at_iso TEXT,
                            updated_at_iso TEXT
                        )
                    ''')
                    
                    # Create virtual table for vector embeddings
                    embedding_dimension = getattr(storage, 'embedding_dimension', 384)
                    storage.conn.execute(f'''
                        CREATE VIRTUAL TABLE IF NOT EXISTS memory_embeddings USING vec0(
                            content_embedding FLOAT[{embedding_dimension}]
                        )
                    ''')
                    
                    # Create indexes for better performance
                    storage.conn.execute('CREATE INDEX IF NOT EXISTS idx_content_hash ON memories(content_hash)')
                    storage.conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)')
                    storage.conn.execute('CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)')
                    
                    storage.conn.commit()
                    return True, "SQLite-vec database repaired"
                    
                except Exception as e:
                    return False, f"SQLite-vec repair failed: {str(e)}"
        
        # ChromaDB backend repair
        elif hasattr(storage, 'collection'):
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
                return True, "ChromaDB successfully repaired"
            else:
                return False, f"ChromaDB repair failed: {message}"
        else:
            return False, f"Unknown storage type: {storage_type}, cannot repair"
                
    except Exception as e:
        logger.error(f"Error repairing database: {str(e)}")
        return False, f"Error repairing database: {str(e)}"