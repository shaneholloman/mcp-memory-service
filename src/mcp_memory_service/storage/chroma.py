"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""

from mcp_memory_service.models.memory import Memory

import chromadb
import json
import sys
import os
import time
import traceback
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Any, Tuple, Set, Optional
from datetime import datetime, date

from .base import MemoryStorage
from ..models.memory import Memory, MemoryQueryResult
from ..utils.hashing import generate_content_hash
from ..utils.system_detection import (
    get_system_info,
    get_optimal_embedding_settings,
    get_torch_device,
    print_system_diagnostics,
    AcceleratorType
)
import mcp.types as types

logger = logging.getLogger(__name__)

# List of models to try in order of preference
# From most capable to least capable
MODEL_FALLBACKS = [
    'all-mpnet-base-v2',      # High quality, larger model
    'all-MiniLM-L6-v2',       # Good balance of quality and size
    'paraphrase-MiniLM-L6-v2', # Alternative with similar size
    'paraphrase-MiniLM-L3-v2', # Smaller model for constrained environments
    'paraphrase-albert-small-v2' # Smallest model, last resort
]

class ChromaMemoryStorage(MemoryStorage):
    def __init__(self, path: str):
        """Initialize ChromaDB storage with hardware-aware embedding function."""
        self.path = path
        self.model = None
        self.embedding_function = None
        self.client = None
        self.collection = None
        self.system_info = get_system_info()
        self.embedding_settings = get_optimal_embedding_settings()
        
        # Log system information
        logger.info(f"Detected system: {self.system_info.os_name} {self.system_info.architecture}")
        logger.info(f"Accelerator: {self.system_info.accelerator}")
        logger.info(f"Memory: {self.system_info.memory_gb:.2f} GB")
        logger.info(f"Using device: {self.embedding_settings['device']}")
        
        # Set environment variables for better cross-platform compatibility
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
        
        # For Apple Silicon, ensure we use MPS when available
        if self.system_info.architecture == "arm64" and self.system_info.os_name == "darwin":
            os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
        
        # For Windows with limited GPU memory, use smaller chunks
        if self.system_info.os_name == "windows" and self.system_info.accelerator == AcceleratorType.CUDA:
            os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
        
        try:
            # Initialize with hardware-aware settings
            self._initialize_embedding_model()
            
            # Initialize ChromaDB with new client format
            logger.info(f"Initializing ChromaDB client at path: {path}")
            self.client = chromadb.PersistentClient(
                path=path
            )
            
            # Get or create collection with proper embedding function
            logger.info("Creating or getting collection...")
            self.collection = self.client.get_or_create_collection(
                name="memory_collection",
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_function
            )
            logger.info("Collection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {str(e)}")
            logger.error(traceback.format_exc())
            # Just log error but don't raise - we'll handle it gracefully
            print(f"ChromaDB initialization error: {str(e)}", file=sys.stderr)
            # We still need to continue initialization for Smithery to work
    
    def _initialize_embedding_model(self):
        """Initialize the embedding model with fallbacks for different hardware."""
        # Start with the optimal model for this system
        preferred_model = self.embedding_settings["model_name"]
        device = self.embedding_settings["device"]
        batch_size = self.embedding_settings["batch_size"]
        
        # Try the preferred model first, then fall back to alternatives
        models_to_try = [preferred_model] + [m for m in MODEL_FALLBACKS if m != preferred_model]
        
        for model_name in models_to_try:
            try:
                logger.info(f"Attempting to load model: {model_name} on {device}")
                start_time = time.time()
                
                # Try to initialize the model with the current settings
                self.model = SentenceTransformer(
                    model_name,
                    device=device
                )
                
                # Set batch size based on available resources
                self.model.max_seq_length = 384  # Default max sequence length
                
                # Test the model with a simple encoding
                _ = self.model.encode("Test encoding", batch_size=batch_size)
                
                load_time = time.time() - start_time
                logger.info(f"Successfully loaded model {model_name} in {load_time:.2f}s")
                
                # Create embedding function for ChromaDB
                self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name,
                    device=device
                )
                
                logger.info(f"Embedding function initialized with model {model_name}")
                return
                
            except Exception as e:
                logger.warning(f"Failed to initialize model {model_name} on {device}: {str(e)}")
                
                # If we're not on CPU already, try falling back to CPU
                if device != "cpu":
                    try:
                        logger.info(f"Falling back to CPU for model: {model_name}")
                        self.model = SentenceTransformer(model_name, device="cpu")
                        _ = self.model.encode("Test encoding", batch_size=max(1, batch_size // 2))
                        
                        # Update settings to reflect CPU usage
                        self.embedding_settings["device"] = "cpu"
                        self.embedding_settings["batch_size"] = max(1, batch_size // 2)
                        
                        # Create embedding function
                        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                            model_name=model_name,
                            device="cpu"
                        )
                        
                        logger.info(f"Successfully loaded model {model_name} on CPU")
                        return
                    except Exception as cpu_e:
                        logger.warning(f"Failed to initialize model {model_name} on CPU: {str(cpu_e)}")
        
        # If we've tried all models and none worked, raise an exception
        error_msg = "Failed to initialize any embedding model. Service may not function correctly."
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        
        # Create a minimal dummy embedding function as last resort
        try:
            logger.warning("Creating minimal dummy embedding function as last resort")
            from sentence_transformers.util import normalize_embeddings
            import numpy as np
            
            # Define a minimal embedding function that returns random vectors
            class MinimalEmbeddingFunction:
                def __call__(self, texts):
                    vectors = [np.random.rand(384) for _ in texts]
                    return normalize_embeddings(np.array(vectors))
            
            self.embedding_function = MinimalEmbeddingFunction()
            logger.warning("Minimal dummy embedding function created. Search quality will be poor.")
        except Exception as e:
            logger.error(f"Failed to create minimal embedding function: {str(e)}")

    def sanitized(self, tags):
        if tags is None:
            return json.dumps([])
        
        # If we get a string, split it into an array
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        # If we get an array, use it directly
        elif isinstance(tags, list):
            tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            return json.dumps([])
                
        # Return JSON string representation of the array
        return json.dumps(tags)

    @staticmethod
    def normalize_timestamp(ts) -> float:
        """Convert datetime or float-like timestamp into float seconds."""
        if isinstance(ts, datetime):
            return time.mktime(ts.timetuple())
        if isinstance(ts, (float, int)):
            return float(ts)
        logger.error(f"Invalid timestamp type: {type(ts)}")
        return time.time()
    
    async def store(self, memory: Memory) -> Tuple[bool, str]:
        """Store a memory with proper embedding handling."""
        try:
            # Check if collection is initialized
            if self.collection is None:
                error_msg = "Collection not initialized, cannot store memory"
                logger.error(error_msg)
                return False, error_msg
                
            # Check for duplicates
            existing = self.collection.get(
                where={"content_hash": memory.content_hash}
            )
            if existing["ids"]:
                return False, "Duplicate content detected"
            
            # Format metadata properly
            metadata = self._format_metadata_for_chroma(memory)
            
            # Add additional metadata
            metadata.update(memory.metadata)

            # Generate ID based on content hash
            memory_id = memory.content_hash
            
            # Add to collection - embedding will be automatically generated
            self.collection.add(
                documents=[memory.content],
                metadatas=[metadata],
                ids=[memory_id]
            )
            
            return True, f"Successfully stored memory with ID: {memory_id}"
            
        except Exception as e:
            error_msg = f"Error storing memory: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    async def search_by_tag(self, tags: List[str]) -> List[Memory]:
        try:
            results = self.collection.get(
                include=["metadatas", "documents"]
            )

            memories = []
            if results["ids"]:
                for i, doc in enumerate(results["documents"]):
                    memory_meta = results["metadatas"][i]
                    
                    # Always expect JSON string in storage
                    try:
                        stored_tags = json.loads(memory_meta.get("tags", "[]"))
                        stored_tags = [str(tag).strip() for tag in stored_tags]
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(f"Invalid tags format in memory: {memory_meta.get('content_hash')}")
                        continue
                    
                    # Normalize search tags
                    search_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
                    
                    if any(search_tag in stored_tags for search_tag in search_tags):
                        memory = Memory(
                            content=doc,
                            content_hash=memory_meta["content_hash"],
                            tags=stored_tags,
                            memory_type=memory_meta.get("type")
                        )
                        memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error searching by tags: {e}")
            return []

    async def delete_by_tag(self, tag: str) -> Tuple[int, str]:
        """Deletes memories that match the specified tag."""
        try:
            # Get all the documents from ChromaDB
            results = self.collection.get(
                include=["metadatas"]
            )

            ids_to_delete = []
            if results["ids"]:
                for i, meta in enumerate(results["metadatas"]):
                    try:
                        retrieved_tags_string = meta.get("tags", "[]")
                        retrieved_tags = json.loads(retrieved_tags_string)
                    except json.JSONDecodeError:
                        retrieved_tags = []

                    if tag in retrieved_tags:
                        ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, f"No memories found with tag: {tag}"

            # Delete memories
            self.collection.delete(ids=ids_to_delete)

            return len(ids_to_delete), f"Successfully deleted {len(ids_to_delete)} memories with tag: {tag}"

        except Exception as e:
            logger.error(f"Error deleting memories by tag: {e}")
            return 0, f"Error deleting memories by tag: {e}"
      
    async def delete(self, content_hash: str) -> Tuple[bool, str]:
        """Delete a memory by its hash."""
        try:
            # First check if the memory exists
            existing = self.collection.get(
                where={"content_hash": content_hash}
            )
            
            if not existing["ids"]:
                return False, f"No memory found with hash {content_hash}"
            
            # Delete the memory
            self.collection.delete(
                where={"content_hash": content_hash}
            )
            
            return True, f"Successfully deleted memory with hash {content_hash}"
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            return False, f"Error deleting memory: {str(e)}"

    async def cleanup_duplicates(self) -> Tuple[int, str]:
        """Remove duplicate memories based on content hash."""
        try:
            # Get all memories
            results = self.collection.get()
            
            if not results["ids"]:
                return 0, "No memories found in database"
            
            # Track seen hashes and duplicates
            seen_hashes: Set[str] = set()
            duplicates = []
            
            for i, metadata in enumerate(results["metadatas"]):
                content_hash = metadata.get("content_hash")
                if not content_hash:
                    # Generate hash if missing
                    content_hash = generate_content_hash(results["documents"][i], metadata)
                
                if content_hash in seen_hashes:
                    duplicates.append(results["ids"][i])
                else:
                    seen_hashes.add(content_hash)
            
            # Delete duplicates if found
            if duplicates:
                self.collection.delete(
                    ids=duplicates
                )
                return len(duplicates), f"Successfully removed {len(duplicates)} duplicate memories"
            
            return 0, "No duplicate memories found"
            
        except Exception as e:
            logger.error(f"Error cleaning up duplicates: {str(e)}")
            return 0, f"Error cleaning up duplicates: {str(e)}"

    async def recall(self, query: Optional[str] = None, n_results: int = 5, start_timestamp: Optional[float] = None, end_timestamp: Optional[float] = None) -> List[MemoryQueryResult]:
        """
        Retrieve memories with combined time filtering and optional semantic search.
        
        Args:
            query: Optional semantic search query. If None, only time filtering is applied.
            n_results: Maximum number of results to return.
            start_timestamp: Optional start time for filtering.
            end_timestamp: Optional end time for filtering.
            
        Returns:
            List of MemoryQueryResult objects.
        """
        try:
            # Check if collection is initialized
            if self.collection is None:
                logger.error("Collection not initialized, cannot retrieve memories")
                return []
                
            # Build time filtering where clause
            where_clause = {}
            if start_timestamp is not None or end_timestamp is not None:
                where_clause = {"$and": []}
                
            if start_timestamp is not None:
                start_timestamp = self.normalize_timestamp(start_timestamp)
                where_clause["$and"].append({"timestamp": {"$gte": int(start_timestamp)}})

            if end_timestamp is not None:
                end_timestamp = self.normalize_timestamp(end_timestamp)
                where_clause["$and"].append({"timestamp": {"$lte": int(end_timestamp)}})

            # If there's no valid where clause, set it to None to avoid ChromaDB errors
            if not where_clause.get("$and", []):
                where_clause = None
                
            # Log the where clause for debugging
            logger.info(f"Time filtering where clause: {where_clause}")
                
            # Determine whether to use semantic search or just time-based filtering
            if query:
                # Combined semantic search with time filtering
                try:
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results,
                        where=where_clause,
                        include=["documents", "metadatas", "distances"]
                    )
                    
                    if not results["ids"] or not results["ids"][0]:
                        return []
                    
                    memory_results = []
                    for i in range(len(results["ids"][0])):
                        metadata = results["metadatas"][0][i]
                        
                        # Parse tags from JSON string
                        try:
                            tags = json.loads(metadata.get("tags", "[]"))
                        except json.JSONDecodeError:
                            tags = []
                        
                        # Reconstruct memory object
                        # timestamp = float(metadata.get("timestamp", time.time()))
                        raw_timestamp = metadata.get("timestamp", time.time())
                        if isinstance(raw_timestamp, datetime):
                            timestamp = time.mktime(raw_timestamp.timetuple())
                        else:
                            timestamp = float(raw_timestamp)
                        memory = Memory(
                            content=results["documents"][0][i],
                            content_hash=metadata["content_hash"],
                            tags=tags,
                            memory_type=metadata.get("memory_type", ""),
                            timestamp=timestamp,
                            metadata={k: v for k, v in metadata.items() 
                                    if k not in ["content_hash", "tags", "memory_type", "timestamp"]}
                        )
                        
                        # Calculate cosine similarity from distance
                        similarity = 1.0 - results["distances"][0][i]
                        
                        memory_results.append(MemoryQueryResult(memory=memory, relevance_score=similarity))
                    
                    return memory_results
                except Exception as query_error:
                    logger.error(f"Error in semantic search: {str(query_error)}")
                    # Fall back to time-based retrieval on error
                    logger.info("Falling back to time-based retrieval")
            
            # Time-based filtering only (or fallback from failed semantic search)
            results = self.collection.get(
                where=where_clause,
                limit=n_results,
                include=["metadatas", "documents"]
            )

            if not results["ids"]:
                return []
                
            memory_results = []
            for i in range(len(results["ids"])):
                metadata = results["metadatas"][i]
                try:
                    retrieved_tags = json.loads(metadata.get("tags", "[]"))
                except json.JSONDecodeError:
                    retrieved_tags = []
                
                # Ensure timestamp is a float
                try:
                    timestamp = float(metadata.get("timestamp", time.time()))
                except (ValueError, TypeError):
                    timestamp = time.time()

                memory = Memory(
                    content=results["documents"][i],
                    content_hash=metadata["content_hash"],
                    tags=retrieved_tags,
                    memory_type=metadata.get("type", ""),
                    timestamp=timestamp,
                    metadata={k: v for k, v in metadata.items() 
                             if k not in ["type", "content_hash", "tags", "timestamp"]}
                )
                # For time-based retrieval, we don't have a relevance score
                memory_results.append(MemoryQueryResult(memory=memory, relevance_score=None))

            return memory_results

        except Exception as e:
            logger.error(f"Error in recall: {str(e)}")
            logger.error(traceback.format_exc())
            return []

    async def delete_by_timeframe(self, start_date: date, end_date: Optional[date] = None, tag: Optional[str] = None) -> Tuple[int, str]:
        """Delete memories within a timeframe and optionally filtered by tag."""
        try:
            if end_date is None:
                end_date = start_date

            start_datetime = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
            end_datetime = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

            start_timestamp = start_datetime.timestamp()
            end_timestamp = end_datetime.timestamp()

            where_clause = {
                "$and": [
                    {"timestamp": {"$gte": start_timestamp}},
                    {"timestamp": {"$lte": end_timestamp}}
                ]
            }

            results = self.collection.get(include=["metadatas"], where=where_clause)
            ids_to_delete = []

            if results.get("ids"):
                for i, meta in enumerate(results["metadatas"]):
                    try:
                        retrieved_tags = json.loads(meta.get("tags", "[]"))
                    except json.JSONDecodeError:
                        retrieved_tags = []

                    if tag is None or tag in retrieved_tags:
                        ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, "No memories found matching the criteria."

            self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete), None

        except Exception as e:
            logger.exception("Error deleting memories by timeframe:")
            return 0, str(e)

    async def delete_before_date(self, before_date: date, tag: Optional[str] = None) -> Tuple[int, str]:
        """Delete memories before a given date and optionally filtered by tag."""
        try:
            before_datetime = datetime(before_date.year, before_date.month, before_date.day, 23, 59, 59)
            before_timestamp = before_datetime.timestamp()

            where_clause = {"timestamp": {"$lt": before_timestamp}}

            results = self.collection.get(include=["metadatas"], where=where_clause)
            ids_to_delete = []

            if results.get("ids"):
                for i, meta in enumerate(results["metadatas"]):
                    try:
                        retrieved_tags = json.loads(meta.get("tags", "[]"))
                    except json.JSONDecodeError:
                        retrieved_tags = []

                    if tag is None or tag in retrieved_tags:
                        ids_to_delete.append(results["ids"][i])

            if not ids_to_delete:
                return 0, "No memories found matching the criteria."

            self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete), None

        except Exception as e:
            logger.exception("Error deleting memories before date:")
            return 0, str(e)


    def _format_metadata_for_chroma(self, memory: Memory) -> Dict[str, Any]:
        """Format metadata to be compatible with ChromaDB requirements with multi-format timestamps."""
        # Ensure timestamps are properly synchronized
        memory._sync_timestamps(
            created_at=memory.created_at,
            created_at_iso=memory.created_at_iso,
            updated_at=memory.updated_at,
            updated_at_iso=memory.updated_at_iso
        )
        
        # Use both new timestamp fields and legacy timestamp fields for compatibility
        metadata = {
            "content_hash": memory.content_hash,
            "memory_type": memory.memory_type if memory.memory_type else "",
            # Store legacy timestamp in all formats for backward compatibility
            "timestamp": int(memory.created_at),
            "timestamp_float": memory.created_at,
            "timestamp_str": memory.created_at_iso,
            # Store new timestamp fields
            "created_at": memory.created_at,
            "created_at_iso": memory.created_at_iso,
            "updated_at": memory.updated_at,
            "updated_at_iso": memory.updated_at_iso
        }
        
        # Log the timestamps for debugging
        logger.debug(f"Storing memory with multi-format timestamps: created_at={memory.created_at}, created_at_iso='{memory.created_at_iso}', updated_at={memory.updated_at}, updated_at_iso='{memory.updated_at_iso}'")
        
        # Properly serialize tags
        if memory.tags:
            if isinstance(memory.tags, list):
                metadata["tags"] = json.dumps([str(tag).strip() for tag in memory.tags if str(tag).strip()])
            elif isinstance(memory.tags, str):
                tags = [tag.strip() for tag in memory.tags.split(",") if tag.strip()]
                metadata["tags"] = json.dumps(tags)
        else:
            metadata["tags"] = "[]"
        
        # Add any additional metadata
        for key, value in memory.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        
        return metadata

    async def retrieve(self, query: str, n_results: int = 5) -> List[MemoryQueryResult]:
        """Retrieve memories using semantic search with hardware-aware optimizations."""
        try:
            # Check if collection is initialized
            if self.collection is None:
                logger.error("Collection not initialized, cannot retrieve memories")
                return []
            
            # Check if embedding function is available
            if self.embedding_function is None:
                logger.error("Embedding function not initialized, cannot retrieve memories")
                return []
            
            start_time = time.time()
            
            try:
                # Query using the embedding function with hardware-aware settings
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=["documents", "metadatas", "distances"]
                )
            except Exception as query_error:
                logger.warning(f"Error during query operation: {str(query_error)}")
                
                # Fallback: Try with direct embedding if the standard query fails
                try:
                    logger.info("Attempting fallback query with direct embedding")
                    
                    # Generate embedding directly
                    if self.model:
                        query_embedding = self.model.encode(
                            query,
                            batch_size=self.embedding_settings["batch_size"],
                            show_progress_bar=False
                        ).tolist()
                        
                        # Use the embedding directly
                        results = self.collection.query(
                            query_embeddings=[query_embedding],
                            n_results=n_results,
                            include=["documents", "metadatas", "distances"]
                        )
                    else:
                        raise ValueError("Model not available for fallback query")
                        
                except Exception as fallback_error:
                    logger.error(f"Fallback query also failed: {str(fallback_error)}")
                    return []
            
            query_time = time.time() - start_time
            logger.debug(f"Query completed in {query_time:.4f}s")
            
            if not results["ids"] or not results["ids"][0]:
                return []
            
            memory_results = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                
                # Parse tags from JSON string if needed
                tags = []
                if "tags" in metadata:
                    try:
                        if isinstance(metadata["tags"], str):
                            tags = json.loads(metadata["tags"])
                        else:
                            tags = metadata["tags"]
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(f"Could not parse tags for memory {metadata.get('content_hash')}")
                
                # Reconstruct memory object
                memory = Memory(
                    content=results["documents"][0][i],
                    content_hash=metadata["content_hash"],
                    tags=tags,
                    memory_type=metadata.get("memory_type", ""),
                )
                
                # Calculate cosine similarity from distance
                distance = results["distances"][0][i]
                similarity = 1 - distance
                
                memory_results.append(MemoryQueryResult(memory, similarity))
            
            return memory_results
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
            logger.error(traceback.format_exc())
            return []