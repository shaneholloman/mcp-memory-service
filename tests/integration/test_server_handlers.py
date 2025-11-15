"""
Integration tests for MCP handler methods in server.py.

These tests verify that the MCP handlers correctly transform MemoryService
responses to MCP TextContent format, particularly after the fix for issue #198.
"""

import pytest
from mcp import types
from mcp_memory_service.server import MemoryServer


class TestHandleStoreMemory:
    """Test suite for handle_store_memory MCP handler."""

    @pytest.mark.asyncio
    async def test_store_memory_success(self):
        """Test storing a valid memory returns success message with hash."""
        server = MemoryServer()

        result = await server.handle_store_memory({
            "content": "Test memory content for integration test",
            "metadata": {
                "tags": ["test", "integration"],
                "type": "note"
            }
        })

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)

        # Verify success message
        text = result[0].text
        assert "successfully" in text.lower()
        assert "hash:" in text.lower()
        assert "..." in text  # Hash should be truncated

    @pytest.mark.asyncio
    async def test_store_memory_chunked(self):
        """Test storing long content creates multiple chunks."""
        server = MemoryServer()

        # Create content that will be auto-split (> 1500 chars)
        long_content = "This is a very long memory content. " * 100

        result = await server.handle_store_memory({
            "content": long_content,
            "metadata": {"tags": ["test"], "type": "note"}
        })

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)

        # Verify chunked message
        text = result[0].text
        assert "chunk" in text.lower()
        assert "successfully" in text.lower()

    @pytest.mark.asyncio
    async def test_store_memory_empty_content(self):
        """Test storing empty content returns error."""
        server = MemoryServer()

        result = await server.handle_store_memory({
            "content": "",
            "metadata": {}
        })

        # Verify error message
        assert isinstance(result, list)
        assert len(result) == 1
        text = result[0].text
        assert "error" in text.lower()
        assert "required" in text.lower()

    @pytest.mark.asyncio
    async def test_store_memory_missing_content(self):
        """Test storing without content parameter returns error."""
        server = MemoryServer()

        result = await server.handle_store_memory({
            "metadata": {"tags": ["test"]}
        })

        # Verify error message
        assert isinstance(result, list)
        assert len(result) == 1
        text = result[0].text
        assert "error" in text.lower()

    @pytest.mark.asyncio
    async def test_store_memory_with_tags_string(self):
        """Test storing memory with tags as string (not array)."""
        server = MemoryServer()

        result = await server.handle_store_memory({
            "content": "Test with string tags",
            "metadata": {
                "tags": "test,integration,string-tags",
                "type": "note"
            }
        })

        # Should succeed - MemoryService handles string tags
        assert isinstance(result, list)
        assert len(result) == 1
        text = result[0].text
        assert "successfully" in text.lower()

    @pytest.mark.asyncio
    async def test_store_memory_default_type(self):
        """Test storing memory without explicit type uses default."""
        server = MemoryServer()

        result = await server.handle_store_memory({
            "content": "Memory without explicit type",
            "metadata": {"tags": ["test"]}
        })

        # Should succeed with default type
        assert isinstance(result, list)
        assert len(result) == 1
        text = result[0].text
        assert "successfully" in text.lower()


class TestHandleRetrieveMemory:
    """Test suite for handle_retrieve_memory MCP handler."""

    @pytest.mark.asyncio
    async def test_retrieve_memory_success(self):
        """Test retrieving memories with valid query."""
        server = MemoryServer()

        # First store a memory
        await server.handle_store_memory({
            "content": "Searchable test memory for retrieval",
            "metadata": {"tags": ["retrieval-test"], "type": "note"}
        })

        # Now retrieve it
        result = await server.handle_retrieve_memory({
            "query": "searchable test memory",
            "n_results": 5
        })

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)

        # Should contain memory data (JSON format)
        text = result[0].text
        assert "searchable test memory" in text.lower() or "retrieval-test" in text.lower()

    @pytest.mark.asyncio
    async def test_retrieve_memory_missing_query(self):
        """Test retrieving without query parameter returns error."""
        server = MemoryServer()

        result = await server.handle_retrieve_memory({
            "n_results": 5
        })

        # Verify error message
        assert isinstance(result, list)
        assert len(result) == 1
        text = result[0].text
        assert "error" in text.lower()
        assert "query" in text.lower()


class TestHandleSearchByTag:
    """Test suite for handle_search_by_tag MCP handler."""

    @pytest.mark.asyncio
    async def test_search_by_tag_success(self):
        """Test searching by tag returns matching memories."""
        server = MemoryServer()

        # Store a memory with specific tag
        await server.handle_store_memory({
            "content": "Memory with unique tag for search",
            "metadata": {"tags": ["unique-search-tag"], "type": "note"}
        })

        # Search by tag
        result = await server.handle_search_by_tag({
            "tags": ["unique-search-tag"]
        })

        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], types.TextContent)

        # Should contain memory data
        text = result[0].text
        assert "unique-search-tag" in text.lower() or "memory with unique tag" in text.lower()

    @pytest.mark.asyncio
    async def test_search_by_tag_missing_tags(self):
        """Test searching without tags parameter returns error."""
        server = MemoryServer()

        result = await server.handle_search_by_tag({})

        # Verify error message
        assert isinstance(result, list)
        assert len(result) == 1
        text = result[0].text
        assert "error" in text.lower()
        assert "tags" in text.lower()


# Regression test for issue #198
class TestIssue198Regression:
    """Regression tests specifically for issue #198 - Response format bug."""

    @pytest.mark.asyncio
    async def test_no_keyerror_on_store_success(self):
        """Verify fix for issue #198: No KeyError on successful store."""
        server = MemoryServer()

        # This would previously raise KeyError: 'message'
        result = await server.handle_store_memory({
            "content": "Test for issue 198 regression",
            "metadata": {"tags": ["issue-198"], "type": "test"}
        })

        # Should return success message without KeyError
        assert isinstance(result, list)
        assert len(result) == 1
        assert "successfully" in result[0].text.lower()
        # Should NOT contain the string "message" (old buggy behavior)
        assert result[0].text != "Error storing memory: 'message'"

    @pytest.mark.asyncio
    async def test_error_handling_without_keyerror(self):
        """Verify fix for issue #198: Errors handled without KeyError."""
        server = MemoryServer()

        # Store with empty content (triggers error path)
        result = await server.handle_store_memory({
            "content": "",
            "metadata": {}
        })

        # Should return error message without KeyError
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0].text.lower()
        # Should NOT be KeyError message
        assert "'message'" not in result[0].text
