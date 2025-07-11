"""Tests for memory metadata update functionality."""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from datetime import datetime
import time

from src.mcp_memory_service.models.memory import Memory
from src.mcp_memory_service.storage.chroma import ChromaMemoryStorage
from src.mcp_memory_service.utils.hashing import generate_content_hash


class TestMemoryMetadataUpdate:
    """Test suite for memory metadata update functionality."""
    
    @pytest.fixture
    async def storage(self):
        """Create a test storage instance."""
        # Use temporary directory for test database
        temp_dir = tempfile.mkdtemp()
        storage = ChromaMemoryStorage(chroma_path=temp_dir)
        await storage.initialize()
        yield storage
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    async def sample_memory(self, storage):
        """Create a sample memory for testing."""
        content = "This is a test memory for metadata updates"
        memory = Memory(
            content=content,
            content_hash=generate_content_hash(content),
            tags=["test", "original"],
            memory_type="note",
            metadata={"priority": "medium", "category": "testing"}
        )
        
        # Store the memory
        success, message = await storage.store(memory)
        assert success, f"Failed to store sample memory: {message}"
        
        return memory
    
    @pytest.mark.asyncio
    async def test_update_tags(self, storage, sample_memory):
        """Test updating memory tags."""
        # Update tags
        new_tags = ["test", "updated", "important"]
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"tags": new_tags}
        )
        
        assert success, f"Failed to update tags: {message}"
        assert "tags" in message
        
        # Verify the update
        results = await storage.retrieve("test memory", n_results=1)
        assert len(results) == 1
        
        updated_memory = results[0].memory
        assert set(updated_memory.tags) == set(new_tags)
        assert updated_memory.content == sample_memory.content
        assert updated_memory.content_hash == sample_memory.content_hash
    
    @pytest.mark.asyncio
    async def test_update_memory_type(self, storage, sample_memory):
        """Test updating memory type."""
        # Update memory type
        new_type = "reminder"
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"memory_type": new_type}
        )
        
        assert success, f"Failed to update memory type: {message}"
        assert "memory_type" in message
        
        # Verify the update
        results = await storage.retrieve("test memory", n_results=1)
        assert len(results) == 1
        
        updated_memory = results[0].memory
        assert updated_memory.memory_type == new_type
        assert updated_memory.content == sample_memory.content
    
    @pytest.mark.asyncio
    async def test_update_custom_metadata(self, storage, sample_memory):
        """Test updating custom metadata fields."""
        # Update custom metadata
        new_metadata = {
            "priority": "high",
            "due_date": "2024-01-15",
            "assignee": "test_user"
        }
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"metadata": new_metadata}
        )
        
        assert success, f"Failed to update metadata: {message}"
        assert "custom_metadata" in message
        
        # Verify the update
        results = await storage.retrieve("test memory", n_results=1)
        assert len(results) == 1
        
        updated_memory = results[0].memory
        # Should merge with existing metadata
        assert updated_memory.metadata["priority"] == "high"
        assert updated_memory.metadata["due_date"] == "2024-01-15"
        assert updated_memory.metadata["assignee"] == "test_user"
        assert updated_memory.metadata["category"] == "testing"  # Original field preserved
    
    @pytest.mark.asyncio
    async def test_update_direct_fields(self, storage, sample_memory):
        """Test updating custom fields directly."""
        # Update custom fields directly
        updates = {
            "priority": "urgent",
            "status": "active",
            "custom_field": "custom_value"
        }
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates=updates
        )
        
        assert success, f"Failed to update direct fields: {message}"
        
        # Verify the update
        results = await storage.retrieve("test memory", n_results=1)
        assert len(results) == 1
        
        updated_memory = results[0].memory
        assert updated_memory.metadata["priority"] == "urgent"
        assert updated_memory.metadata["status"] == "active"
        assert updated_memory.metadata["custom_field"] == "custom_value"
    
    @pytest.mark.asyncio
    async def test_preserve_timestamps_true(self, storage, sample_memory):
        """Test that timestamps are preserved when preserve_timestamps=True."""
        original_created_at = sample_memory.created_at
        original_created_at_iso = sample_memory.created_at_iso
        
        # Wait a moment to ensure timestamp difference
        await asyncio.sleep(0.1)
        
        # Update with preserve_timestamps=True (default)
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"tags": ["updated"]},
            preserve_timestamps=True
        )
        
        assert success, f"Failed to update with preserved timestamps: {message}"
        
        # Verify timestamps
        results = await storage.retrieve("test memory", n_results=1)
        updated_memory = results[0].memory
        
        # created_at should be preserved (within small tolerance for floating point)
        assert abs(updated_memory.created_at - original_created_at) < 0.01
        assert updated_memory.created_at_iso == original_created_at_iso
        
        # updated_at should be newer
        assert updated_memory.updated_at > original_created_at
    
    @pytest.mark.asyncio
    async def test_preserve_timestamps_false(self, storage, sample_memory):
        """Test that timestamps are reset when preserve_timestamps=False."""
        original_created_at = sample_memory.created_at
        
        # Wait a moment to ensure timestamp difference
        await asyncio.sleep(0.1)
        
        # Update with preserve_timestamps=False
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"tags": ["updated"]},
            preserve_timestamps=False
        )
        
        assert success, f"Failed to update with reset timestamps: {message}"
        
        # Verify timestamps
        results = await storage.retrieve("test memory", n_results=1)
        updated_memory = results[0].memory
        
        # created_at should be updated (newer than original)
        assert updated_memory.created_at > original_created_at
    
    @pytest.mark.asyncio
    async def test_memory_not_found(self, storage):
        """Test error handling when memory is not found."""
        nonexistent_hash = "nonexistent123456789"
        
        success, message = await storage.update_memory_metadata(
            content_hash=nonexistent_hash,
            updates={"tags": ["test"]}
        )
        
        assert not success
        assert "not found" in message.lower()
        assert nonexistent_hash in message
    
    @pytest.mark.asyncio
    async def test_invalid_tags_format(self, storage, sample_memory):
        """Test error handling for invalid tags format."""
        # Try to update with invalid tags format
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"tags": "not_a_list"}
        )
        
        assert not success
        assert "list of strings" in message.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_metadata_format(self, storage, sample_memory):
        """Test error handling for invalid metadata format."""
        # Try to update with invalid metadata format
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"metadata": "not_a_dict"}
        )
        
        assert not success
        assert "dictionary" in message.lower()
    
    @pytest.mark.asyncio
    async def test_combined_updates(self, storage, sample_memory):
        """Test updating multiple fields in a single operation."""
        updates = {
            "tags": ["combined", "update", "test"],
            "memory_type": "task",
            "metadata": {
                "priority": "high",
                "deadline": "2024-02-01"
            },
            "status": "pending",
            "category": "work"
        }
        
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates=updates
        )
        
        assert success, f"Failed to perform combined updates: {message}"
        
        # Verify all updates
        results = await storage.retrieve("test memory", n_results=1)
        updated_memory = results[0].memory
        
        assert set(updated_memory.tags) == {"combined", "update", "test"}
        assert updated_memory.memory_type == "task"
        assert updated_memory.metadata["priority"] == "high"
        assert updated_memory.metadata["deadline"] == "2024-02-01"
        assert updated_memory.metadata["status"] == "pending"
        assert updated_memory.metadata["category"] == "work"
        
        # Original content should be unchanged
        assert updated_memory.content == sample_memory.content
        assert updated_memory.content_hash == sample_memory.content_hash
    
    @pytest.mark.asyncio
    async def test_empty_updates(self, storage, sample_memory):
        """Test behavior with empty updates dictionary."""
        # Update with empty dictionary
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={}
        )
        
        # Should succeed but only update the updated_at timestamp
        assert success, f"Failed with empty updates: {message}"
        assert "updated_at" in message
    
    @pytest.mark.asyncio
    async def test_content_preservation(self, storage, sample_memory):
        """Test that content and embeddings are preserved during updates."""
        # Store original content and perform update
        original_content = sample_memory.content
        original_hash = sample_memory.content_hash
        
        success, message = await storage.update_memory_metadata(
            content_hash=sample_memory.content_hash,
            updates={"tags": ["preservation_test"]}
        )
        
        assert success, f"Failed to update: {message}"
        
        # Retrieve and verify content preservation
        results = await storage.retrieve("test memory", n_results=1)
        updated_memory = results[0].memory
        
        assert updated_memory.content == original_content
        assert updated_memory.content_hash == original_hash
        
        # Verify semantic search still works (embeddings preserved)
        semantic_results = await storage.retrieve("metadata updates", n_results=1)
        assert len(semantic_results) == 1
        assert semantic_results[0].memory.content_hash == original_hash


if __name__ == "__main__":
    # Run basic test when executed directly
    async def run_basic_test():
        """Run a basic test to verify functionality."""
        print("Running basic memory metadata update test...")
        
        # Create test storage
        temp_dir = tempfile.mkdtemp()
        storage = ChromaMemoryStorage(chroma_path=temp_dir)
        await storage.initialize()
        
        try:
            # Create test memory
            content = "Test memory for metadata updates"
            memory = Memory(
                content=content,
                content_hash=generate_content_hash(content),
                tags=["test"],
                memory_type="note"
            )
            
            # Store memory
            success, message = await storage.store(memory)
            print(f"Store result: {success}, {message}")
            
            # Update metadata
            success, message = await storage.update_memory_metadata(
                content_hash=memory.content_hash,
                updates={
                    "tags": ["test", "updated"],
                    "memory_type": "reminder",
                    "priority": "high"
                }
            )
            print(f"Update result: {success}, {message}")
            
            # Verify update
            results = await storage.retrieve("test memory", n_results=1)
            if results:
                updated_memory = results[0].memory
                print(f"Updated tags: {updated_memory.tags}")
                print(f"Updated type: {updated_memory.memory_type}")
                print(f"Updated metadata: {updated_memory.metadata}")
                print("✅ Basic test passed!")
            else:
                print("❌ No results found")
                
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Run the test
    asyncio.run(run_basic_test())