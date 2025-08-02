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
Memory CRUD endpoints for the HTTP interface.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from ...storage.sqlite_vec import SqliteVecMemoryStorage
from ...models.memory import Memory
from ...utils.hashing import generate_content_hash
from ..dependencies import get_storage
from ..sse import sse_manager, create_memory_stored_event, create_memory_deleted_event

router = APIRouter()
logger = logging.getLogger(__name__)


# Request/Response Models
class MemoryCreateRequest(BaseModel):
    """Request model for creating a new memory."""
    content: str = Field(..., description="The memory content to store")
    tags: List[str] = Field(default=[], description="Tags to categorize the memory")
    memory_type: Optional[str] = Field(None, description="Type of memory (e.g., 'note', 'reminder', 'fact')")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata for the memory")


class MemoryResponse(BaseModel):
    """Response model for memory data."""
    content: str
    content_hash: str
    tags: List[str]
    memory_type: Optional[str]
    metadata: Dict[str, Any]
    created_at: Optional[float]
    created_at_iso: Optional[str]
    updated_at: Optional[float]  
    updated_at_iso: Optional[str]


class MemoryListResponse(BaseModel):
    """Response model for paginated memory list."""
    memories: List[MemoryResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MemoryCreateResponse(BaseModel):
    """Response model for memory creation."""
    success: bool
    message: str
    content_hash: Optional[str] = None
    memory: Optional[MemoryResponse] = None


class MemoryDeleteResponse(BaseModel):
    """Response model for memory deletion."""
    success: bool
    message: str
    content_hash: str


def memory_to_response(memory: Memory) -> MemoryResponse:
    """Convert Memory model to response format."""
    return MemoryResponse(
        content=memory.content,
        content_hash=memory.content_hash,
        tags=memory.tags,
        memory_type=memory.memory_type,
        metadata=memory.metadata,
        created_at=memory.created_at,
        created_at_iso=memory.created_at_iso,
        updated_at=memory.updated_at,
        updated_at_iso=memory.updated_at_iso
    )


@router.post("/memories", response_model=MemoryCreateResponse, tags=["memories"])
async def store_memory(
    request: MemoryCreateRequest,
    storage: SqliteVecMemoryStorage = Depends(get_storage)
):
    """
    Store a new memory.
    
    Creates a new memory entry with the provided content, tags, and metadata.
    The system automatically generates a unique hash for the content.
    """
    try:
        # Generate content hash
        content_hash = generate_content_hash(request.content)
        
        # Create memory object
        memory = Memory(
            content=request.content,
            content_hash=content_hash,
            tags=request.tags,
            memory_type=request.memory_type,
            metadata=request.metadata
        )
        
        # Store the memory
        success, message = await storage.store(memory)
        
        if success:
            # Broadcast SSE event for successful memory storage
            try:
                memory_data = {
                    "content_hash": content_hash,
                    "content": memory.content,
                    "tags": memory.tags,
                    "memory_type": memory.memory_type
                }
                event = create_memory_stored_event(memory_data)
                await sse_manager.broadcast_event(event)
            except Exception as e:
                # Don't fail the request if SSE broadcasting fails
                logger.warning(f"Failed to broadcast memory_stored event: {e}")
            
            return MemoryCreateResponse(
                success=True,
                message=message,
                content_hash=content_hash,
                memory=memory_to_response(memory)
            )
        else:
            return MemoryCreateResponse(
                success=False,
                message=message,
                content_hash=content_hash
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@router.get("/memories", response_model=MemoryListResponse, tags=["memories"])
async def list_memories(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of memories per page"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    storage: SqliteVecMemoryStorage = Depends(get_storage)
):
    """
    List memories with pagination.
    
    Retrieves memories with optional filtering by tag or memory type.
    Results are paginated for better performance.
    """
    try:
        # For now, we'll implement a basic listing
        # TODO: Implement proper pagination and filtering in storage layer
        
        if tag:
            # Filter by tag
            memories = await storage.search_by_tag([tag])
        else:
            # Get all memories (this is a placeholder - we need a proper list method)
            # For now, let's retrieve with a generic query to get recent memories
            results = await storage.retrieve("", n_results=100)  # Get more results for pagination
            memories = [result.memory for result in results]
        
        # Apply memory_type filter if specified
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        # Calculate pagination
        total = len(memories)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_memories = memories[start_idx:end_idx]
        has_more = end_idx < total
        
        return MemoryListResponse(
            memories=[memory_to_response(m) for m in page_memories],
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list memories: {str(e)}")


@router.get("/memories/{content_hash}", response_model=MemoryResponse, tags=["memories"])
async def get_memory(
    content_hash: str,
    storage: SqliteVecMemoryStorage = Depends(get_storage)
):
    """
    Get a specific memory by its content hash.
    
    Retrieves a single memory entry using its unique content hash identifier.
    """
    try:
        # Since we don't have a direct get_by_hash method, we'll search by hash
        # This is inefficient but works for now - TODO: add get_by_hash to storage
        results = await storage.retrieve(content_hash, n_results=1)
        
        if not results:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Check if the result actually matches the hash
        memory = results[0].memory
        if memory.content_hash != content_hash:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return memory_to_response(memory)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory: {str(e)}")


@router.delete("/memories/{content_hash}", response_model=MemoryDeleteResponse, tags=["memories"])
async def delete_memory(
    content_hash: str,
    storage: SqliteVecMemoryStorage = Depends(get_storage)
):
    """
    Delete a memory by its content hash.
    
    Permanently removes a memory entry from the storage.
    """
    try:
        success, message = await storage.delete(content_hash)
        
        # Broadcast SSE event for memory deletion
        try:
            event = create_memory_deleted_event(content_hash, success)
            await sse_manager.broadcast_event(event)
        except Exception as e:
            # Don't fail the request if SSE broadcasting fails
            logger.warning(f"Failed to broadcast memory_deleted event: {e}")
        
        return MemoryDeleteResponse(
            success=success,
            message=message,
            content_hash=content_hash
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")