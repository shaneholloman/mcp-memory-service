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

"""Debug utilities for memory service."""
from typing import Dict, Any, List
import numpy as np
from ..models.memory import Memory, MemoryQueryResult

def get_raw_embedding(storage, content: str) -> Dict[str, Any]:
    """Get raw embedding vector for content."""
    try:
        embedding = storage.model.encode(content).tolist()
        return {
            "status": "success",
            "embedding": embedding,
            "dimension": len(embedding)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def check_embedding_model(storage) -> Dict[str, Any]:
    """Check if embedding model is loaded and working."""
    try:
        test_embedding = storage.model.encode("test").tolist()
        return {
            "status": "healthy",
            "model_loaded": True,
            "model_name": storage.model._model_card_vars.get('modelname', 'unknown'),
            "embedding_dimension": len(test_embedding)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def debug_retrieve_memory(
    storage,
    query: str,
    n_results: int = 5,
    similarity_threshold: float = 0.0
) -> List[MemoryQueryResult]:
    """Retrieve memories with debug information including raw similarity scores."""
    try:
        query_embedding = storage.model.encode(query).tolist()
        results = storage.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        memory_results = []
        for i in range(len(results["ids"][0])):
            memory = Memory.from_dict(
                {
                    "content": results["documents"][0][i],
                    **results["metadatas"][0][i]
                },
                embedding=results["embeddings"][0][i] if "embeddings" in results else None
            )
            similarity = 1 - results["distances"][0][i]
            
            # Only include results above threshold
            if similarity >= similarity_threshold:
                memory_results.append(
                    MemoryQueryResult(
                        memory=memory,
                        relevance_score=similarity,
                        debug_info={
                            "raw_similarity": similarity,
                            "raw_distance": results["distances"][0][i],
                            "memory_id": results["ids"][0][i]
                        }
                    )
                )
        
        return memory_results
    except Exception as e:
        return []

async def exact_match_retrieve(storage, content: str) -> List[Memory]:
    """Retrieve memories using exact content match."""
    try:
        results = storage.collection.get(
            where={"content": content}
        )
        
        memories = []
        for i in range(len(results["ids"])):
            memory = Memory.from_dict(
                {
                    "content": results["documents"][i],
                    **results["metadatas"][i]
                },
                embedding=results["embeddings"][i] if "embeddings" in results else None
            )
            memories.append(memory)
        
        return memories
    except Exception as e:
        return []