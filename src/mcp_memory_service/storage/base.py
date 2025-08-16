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

"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from ..models.memory import Memory, MemoryQueryResult

class MemoryStorage(ABC):
    """Abstract base class for memory storage implementations."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend."""
        pass
    
    @abstractmethod
    async def store(self, memory: Memory) -> Tuple[bool, str]:
        """Store a memory. Returns (success, message)."""
        pass
    
    @abstractmethod
    async def retrieve(self, query: str, n_results: int = 5) -> List[MemoryQueryResult]:
        """Retrieve memories by semantic search."""
        pass
    
    @abstractmethod
    async def search_by_tag(self, tags: List[str]) -> List[Memory]:
        """Search memories by tags."""
        pass
    
    @abstractmethod
    async def delete(self, content_hash: str) -> Tuple[bool, str]:
        """Delete a memory by its hash."""
        pass
    
    @abstractmethod
    async def delete_by_tag(self, tag: str) -> Tuple[int, str]:
        """Delete memories by tag. Returns (count_deleted, message)."""
        pass
    
    @abstractmethod
    async def cleanup_duplicates(self) -> Tuple[int, str]:
        """Remove duplicate memories. Returns (count_removed, message)."""
        pass
    
    @abstractmethod
    async def update_memory_metadata(self, content_hash: str, updates: Dict[str, Any], preserve_timestamps: bool = True) -> Tuple[bool, str]:
        """
        Update memory metadata without recreating the entire memory entry.
        
        Args:
            content_hash: Hash of the memory to update
            updates: Dictionary of metadata fields to update
            preserve_timestamps: Whether to preserve original created_at timestamp
            
        Returns:
            Tuple of (success, message)
            
        Note:
            - Only metadata, tags, and memory_type can be updated
            - Content and content_hash cannot be modified
            - updated_at timestamp is always refreshed
            - created_at is preserved unless preserve_timestamps=False
        """
        pass
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics. Override for specific implementations."""
        return {
            "total_memories": 0,
            "storage_backend": self.__class__.__name__,
            "status": "operational"
        }
    
    async def get_all_tags(self) -> List[str]:
        """Get all unique tags in the storage. Override for specific implementations."""
        return []
    
    async def get_recent_memories(self, n: int = 10) -> List[Memory]:
        """Get n most recent memories. Override for specific implementations."""
        return []
    
    async def recall_memory(self, query: str, n_results: int = 5) -> List[Memory]:
        """Recall memories based on natural language time expression. Override for specific implementations."""
        # Default implementation just uses regular search
        results = await self.retrieve(query, n_results)
        return [r.memory for r in results]
    
    async def search(self, query: str, n_results: int = 5) -> List[MemoryQueryResult]:
        """Search memories. Default implementation uses retrieve."""
        return await self.retrieve(query, n_results)