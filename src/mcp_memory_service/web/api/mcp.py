"""
MCP (Model Context Protocol) endpoints for Claude Code integration.

This module provides MCP protocol endpoints that allow Claude Code clients
to directly access memory operations using the MCP standard.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..dependencies import get_storage
from ...utils.hashing import generate_content_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPRequest(BaseModel):
    """MCP protocol request structure."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """MCP protocol response structure."""
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


# Define MCP tools available
MCP_TOOLS = [
    MCPTool(
        name="store_memory",
        description="Store a new memory with optional tags and metadata",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory content to store"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags for the memory"},
                "memory_type": {"type": "string", "description": "Optional memory type"}
            },
            "required": ["content"]
        }
    ),
    MCPTool(
        name="retrieve_memory", 
        description="Search and retrieve memories using semantic similarity",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for finding relevant memories"},
                "limit": {"type": "integer", "description": "Maximum number of memories to return", "default": 10}
            },
            "required": ["query"]
        }
    ),
    MCPTool(
        name="search_by_tag",
        description="Search memories by specific tags",
        inputSchema={
            "type": "object", 
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to search for"},
                "operation": {"type": "string", "enum": ["AND", "OR"], "description": "Tag search operation", "default": "AND"}
            },
            "required": ["tags"]
        }
    ),
    MCPTool(
        name="delete_memory",
        description="Delete a specific memory by content hash",
        inputSchema={
            "type": "object",
            "properties": {
                "content_hash": {"type": "string", "description": "Hash of the memory to delete"}
            },
            "required": ["content_hash"]
        }
    ),
    MCPTool(
        name="check_database_health",
        description="Check the health and status of the memory database",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    )
]


@router.post("/")
@router.post("")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP protocol endpoint for processing MCP requests."""
    try:
        storage = get_storage()
        
        if request.method == "initialize":
            return MCPResponse(
                id=request.id,
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "mcp-memory-service",
                        "version": "4.1.1"
                    }
                }
            )

        elif request.method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={
                    "tools": [tool.dict() for tool in MCP_TOOLS]
                }
            )
        
        elif request.method == "tools/call":
            tool_name = request.params.get("name") if request.params else None
            arguments = request.params.get("arguments", {}) if request.params else {}
            
            result = await handle_tool_call(storage, tool_name, arguments)
            
            return MCPResponse(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                }
            )
        
        else:
            return MCPResponse(
                id=request.id,
                error={
                    "code": -32601,
                    "message": f"Method not found: {request.method}"
                }
            )
            
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return MCPResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        )


async def handle_tool_call(storage, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tool calls and route to appropriate memory operations."""
    
    if tool_name == "store_memory":
        from mcp_memory_service.models.memory import Memory
        
        content = arguments.get("content")
        tags = arguments.get("tags", [])
        memory_type = arguments.get("memory_type")
        content_hash = generate_content_hash(content, arguments.get("metadata", {}))
        
        memory = Memory(
            content=content,
            content_hash=content_hash,
            tags=tags,
            memory_type=memory_type
        )
        
        success, message = await storage.store(memory)
        
        return {
            "success": success,
            "message": message,
            "content_hash": memory.content_hash if success else None
        }
    
    elif tool_name == "retrieve_memory":
        query = arguments.get("query")
        limit = arguments.get("limit", 10)
        
        results = await storage.retrieve(query=query, n_results=limit)
        
        return {
            "results": [
                {
                    "content": r.memory.content,
                    "content_hash": r.memory.content_hash,
                    "tags": r.memory.tags,
                    "similarity_score": r.relevance_score,
                    "created_at": r.memory.created_at_iso
                }
                for r in results
            ],
            "total_found": len(results)
        }
    
    elif tool_name == "search_by_tag":
        tags = arguments.get("tags")
        operation = arguments.get("operation", "AND")
        
        results = await storage.search_by_tags(tags=tags, operation=operation)
        
        return {
            "results": [
                {
                    "content": memory.content,
                    "content_hash": memory.content_hash,
                    "tags": memory.tags,
                    "created_at": memory.created_at_iso
                }
                for memory in results
            ],
            "total_found": len(results)
        }
    
    elif tool_name == "delete_memory":
        content_hash = arguments.get("content_hash")
        
        success = await storage.delete_memory(content_hash)
        
        return {
            "success": success,
            "message": f"Memory {'deleted' if success else 'not found'}"
        }
    
    elif tool_name == "check_database_health":
        stats = storage.get_stats()
        
        return {
            "status": "healthy",
            "statistics": stats
        }
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


@router.get("/tools")
async def list_mcp_tools():
    """List available MCP tools for discovery."""
    return {
        "tools": [tool.dict() for tool in MCP_TOOLS],
        "protocol": "mcp",
        "version": "1.0"
    }


@router.get("/health")
async def mcp_health():
    """MCP-specific health check."""
    storage = get_storage()
    stats = storage.get_stats()
    
    return {
        "status": "healthy",
        "protocol": "mcp",
        "tools_available": len(MCP_TOOLS),
        "storage_backend": "sqlite-vec",
        "statistics": stats
    }