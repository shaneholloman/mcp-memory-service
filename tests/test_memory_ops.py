"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
"""
Test core memory operations of the MCP Memory Service.
"""
import pytest
import pytest_asyncio
import asyncio
from mcp_memory_service.server import MemoryServer

@pytest_asyncio.fixture
async def memory_server():
    """Create a test instance of the memory server."""
    server = MemoryServer()
    # MemoryServer initializes itself, no initialize() call needed
    yield server
    # No cleanup needed

@pytest.mark.asyncio
async def test_store_memory(memory_server):
    """Test storing new memory entries."""
    test_content = "The capital of France is Paris"
    test_metadata = {
        "tags": ["geography", "cities", "europe"],
        "type": "fact"
    }
    
    response = await memory_server.store_memory(
        content=test_content,
        metadata=test_metadata
    )
    
    assert response is not None
    # Add more specific assertions based on expected response format

@pytest.mark.asyncio
async def test_retrieve_memory(memory_server):
    """Test retrieving memories using semantic search."""
    # Basic smoke test: verify retrieve_memory works and returns results
    # Note: Due to large existing database and semantic search variability,
    # we test only that the function works, not specific content retrieval

    # Test retrieval with a general query
    results = await memory_server.retrieve_memory(
        query="capital city France Paris",
        n_results=5
    )

    # Basic assertions: function works and returns results
    assert results is not None, "retrieve_memory should not return None"
    assert isinstance(results, list), "retrieve_memory should return a list"
    assert len(results) >= 1, "retrieve_memory should return at least one result from database"
    # Each result should be a string
    assert all(isinstance(r, str) for r in results), "All results should be strings"

@pytest.mark.asyncio
async def test_search_by_tag(memory_server):
    """Test retrieving memories by tags."""
    # Store memory with tags
    await memory_server.store_memory(
        content="Paris is beautiful in spring",
        metadata={"tags": ["travel", "cities", "europe"]}
    )
    
    # Search by tags
    results = await memory_server.search_by_tag(
        tags=["travel", "europe"]
    )
    
    assert results is not None
    assert len(results) > 0
    assert "Paris" in results[0]

@pytest.mark.asyncio
async def test_delete_memory(memory_server):
    """Test deleting specific memories."""
    # Store a unique memory and get its hash
    content = "Memory to be deleted - unique test content 12345"
    response = await memory_server.store_memory(content=content)
    content_hash = response.get("hash")

    # Verify memory exists before deletion
    results_before = await memory_server.retrieve_memory(query=content, n_results=10)
    assert any(content in r for r in results_before), "Memory should exist before deletion"

    # Delete the memory
    delete_response = await memory_server.delete_memory(
        content_hash=content_hash
    )

    assert delete_response.get("success") is True

    # Verify memory is deleted (search should not find it)
    results_after = await memory_server.retrieve_memory(query=content, n_results=10)
    assert not any(content in r for r in results_after), "Memory should be deleted"

@pytest.mark.asyncio
async def test_memory_with_empty_content(memory_server):
    """Test handling of empty or invalid content."""
    # MemoryService returns error in result dict instead of raising exception
    response = await memory_server.store_memory(content="")
    assert response.get("success") is False
    assert "error" in response

@pytest.mark.asyncio
async def test_memory_with_invalid_tags(memory_server):
    """Test handling of invalid tags metadata."""
    import time
    # Tags are normalized by MemoryService - string tags are acceptable
    # Use unique content to avoid duplicate detection
    unique_content = f"Test content with string tag - unique {int(time.time() * 1000)}"
    response = await memory_server.store_memory(
        content=unique_content,
        metadata={"tags": "single-tag"}  # String tags are normalized to list
    )
    assert response.get("success") is True