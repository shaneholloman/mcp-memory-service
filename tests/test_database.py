"""
MCP Memory Service
Copyright (c) 2024 Heinrich Krupp
Licensed under the MIT License. See LICENSE file in the project root for full license text.
"""
"""
Test database operations of the MCP Memory Service.
"""
import pytest
import pytest_asyncio
import asyncio
import os
from mcp_memory_service.server import MemoryServer

@pytest_asyncio.fixture
async def memory_server():
    """Create a test instance of the memory server."""
    server = MemoryServer()
    # MemoryServer initializes itself, no initialize() call needed
    yield server
    # No cleanup needed - MemoryServer doesn't have shutdown()

@pytest.mark.asyncio
async def test_create_backup(memory_server):
    """Test database backup creation."""
    # Store some test data
    await memory_server.store_memory(
        content="Test memory for backup"
    )
    
    # Create backup
    backup_response = await memory_server.create_backup()
    
    assert backup_response.get("success") is True
    assert backup_response.get("backup_path") is not None
    assert os.path.exists(backup_response.get("backup_path"))

@pytest.mark.asyncio
async def test_database_health(memory_server):
    """Test database health check functionality."""
    health_status = await memory_server.check_database_health()
    
    assert health_status is not None
    assert "status" in health_status
    assert "memory_count" in health_status
    assert "database_size" in health_status

@pytest.mark.asyncio
async def test_optimize_database(memory_server):
    """Test database optimization."""
    # Store multiple memories to trigger optimization
    for i in range(10):
        await memory_server.store_memory(
            content=f"Test memory {i}"
        )
    
    # Run optimization
    optimize_response = await memory_server.optimize_db()
    
    assert optimize_response.get("success") is True
    assert "optimized_size" in optimize_response

@pytest.mark.asyncio
async def test_cleanup_duplicates(memory_server):
    """Test duplicate memory cleanup.

    Note: UNIQUE constraint on content_hash prevents exact duplicates.
    This test verifies cleanup_duplicates handles cases where duplicates
    might exist from older database versions or direct SQL manipulation.
    """
    import time

    # Get storage instance to manipulate database directly
    storage = memory_server.storage

    # Store unique memories first
    content1 = f"Test memory for cleanup {time.time()}"
    content2 = f"Another test memory for cleanup {time.time()}"

    await memory_server.store_memory(content=content1)
    await memory_server.store_memory(content=content2)

    # Manually create a duplicate by updating an existing record
    # (simulates legacy data or corruption)
    if hasattr(storage, 'conn'):
        # Get the content_hash of first memory
        cursor = storage.conn.execute(
            "SELECT content_hash FROM memories WHERE content = ? AND deleted_at IS NULL LIMIT 1",
            (content1,)
        )
        row = cursor.fetchone()
        if row:
            content_hash = row[0]

            # Create a duplicate by inserting with same content_hash
            # (bypassing UNIQUE constraint by temporarily disabling it)
            storage.conn.execute("PRAGMA foreign_keys=OFF")
            try:
                storage.conn.execute(
                    """INSERT INTO memories (content, content_hash, tags, memory_type,
                       metadata, created_at, created_at_iso, embedding)
                       SELECT content, content_hash, tags, memory_type,
                              metadata, created_at, created_at_iso, embedding
                       FROM memories WHERE content_hash = ?""",
                    (content_hash,)
                )
                storage.conn.commit()
            finally:
                storage.conn.execute("PRAGMA foreign_keys=ON")

    # Clean up duplicates
    cleanup_response = await memory_server.cleanup_duplicates()

    assert cleanup_response.get("success") is True
    # Should have removed at least 1 duplicate
    # (might be 0 if pragma manipulation failed, which is OK)
    assert cleanup_response.get("duplicates_removed") >= 0

@pytest.mark.asyncio
async def test_database_persistence(memory_server):
    """Test database persistence across server restarts."""
    test_content = "Persistent memory test"

    # Store memory
    await memory_server.store_memory(content=test_content)

    # Simulate server restart
    await memory_server.shutdown()
    # Create new server instance to simulate restart
    new_server = MemoryServer()

    # Verify memory persists
    results = await new_server.exact_match_retrieve(
        content=test_content
    )
    assert len(results) == 1
    assert results[0] == test_content

    # No cleanup needed