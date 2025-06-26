"""
Comprehensive tests for timestamp-based memory recall functionality
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta, date
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_memory_service.models.memory import Memory
from mcp_memory_service.storage.chroma import ChromaMemoryStorage
from mcp_memory_service.utils.hashing import generate_content_hash
from mcp_memory_service.utils.time_parser import extract_time_expression, parse_time_expression


class TestTimestampRecall:
    """Test class for timestamp-based memory recall"""
    
    @pytest.fixture
    async def storage(self, tmp_path):
        """Create a temporary storage instance for testing"""
        storage_path = str(tmp_path / "test_chroma_db")
        storage = ChromaMemoryStorage(storage_path, preload_model=True)
        yield storage
        # Cleanup happens automatically with tmp_path
    
    @pytest.fixture
    async def populated_storage(self, storage):
        """Create a storage instance with test memories"""
        # Create memories at specific timestamps
        now = time.time()
        test_data = [
            # Today's memories
            {"content": "Morning coffee", "offset": 0, "tags": ["today", "morning"]},
            {"content": "Lunch meeting", "offset": -4 * 3600, "tags": ["today", "afternoon"]},
            {"content": "Evening workout", "offset": -8 * 3600, "tags": ["today", "evening"]},
            
            # Yesterday's memories
            {"content": "Yesterday morning", "offset": -24 * 3600, "tags": ["yesterday", "morning"]},
            {"content": "Yesterday lunch", "offset": -28 * 3600, "tags": ["yesterday", "afternoon"]},
            
            # Last week's memories
            {"content": "Last Monday meeting", "offset": -7 * 24 * 3600, "tags": ["lastweek", "monday"]},
            {"content": "Last Friday party", "offset": -3 * 24 * 3600, "tags": ["lastweek", "friday"]},
            
            # Last month's memories
            {"content": "Monthly review", "offset": -30 * 24 * 3600, "tags": ["lastmonth", "review"]},
            
            # Specific date memories (for precise testing)
            {"content": "New Year 2025", "timestamp": datetime(2025, 1, 1, 12, 0, 0).timestamp(), "tags": ["holiday"]},
            {"content": "Valentine's Day", "timestamp": datetime(2025, 2, 14, 18, 0, 0).timestamp(), "tags": ["holiday"]},
        ]
        
        # Store all memories
        for data in test_data:
            if "timestamp" in data:
                timestamp = data["timestamp"]
            else:
                timestamp = now + data["offset"]
            
            memory = Memory(
                content=data["content"],
                content_hash=generate_content_hash(data["content"]),
                tags=data["tags"],
                created_at=timestamp,
                updated_at=timestamp
            )
            await storage.store(memory)
        
        return storage
    
    @pytest.mark.asyncio
    async def test_timestamp_precision(self, storage):
        """Test that timestamps are stored with full float precision"""
        # Create memories with sub-second precision
        base_time = time.time()
        memories = []
        
        for i in range(5):
            timestamp = base_time + (i * 0.1)  # 0.1 second intervals
            memory = Memory(
                content=f"Memory {i}",
                content_hash=generate_content_hash(f"Memory {i}"),
                created_at=timestamp,
                updated_at=timestamp
            )
            success, _ = await storage.store(memory)
            assert success
            memories.append((timestamp, f"Memory {i}"))
        
        # Verify each memory has unique timestamp
        all_data = storage.collection.get(include=["metadatas", "documents"])
        stored_timestamps = [m.get("timestamp") for m in all_data["metadatas"]]
        
        # All timestamps should be unique
        assert len(set(stored_timestamps)) == len(stored_timestamps)
        
        # All timestamps should be floats
        for ts in stored_timestamps:
            assert isinstance(ts, float)
    
    @pytest.mark.asyncio
    async def test_natural_language_time_parsing(self):
        """Test parsing of various natural language time expressions"""
        test_cases = [
            ("yesterday", True),
            ("last week", True),
            ("2 days ago", True),
            ("last month", True),
            ("this morning", True),
            ("last summer", True),
            ("christmas", True),
            ("first quarter of 2024", True),
            ("random text", False),
        ]
        
        for query, should_parse in test_cases:
            start_ts, end_ts = parse_time_expression(query)
            if should_parse:
                assert start_ts is not None or end_ts is not None, f"Failed to parse: {query}"
            else:
                assert start_ts is None and end_ts is None, f"Incorrectly parsed: {query}"
    
    @pytest.mark.asyncio
    async def test_recall_yesterday(self, populated_storage):
        """Test recalling memories from yesterday"""
        results = await populated_storage.recall(
            query="yesterday",
            n_results=10
        )
        
        # We should get yesterday's memories
        assert len(results) == 2
        contents = [r.memory.content for r in results]
        assert "Yesterday morning" in contents
        assert "Yesterday lunch" in contents
    
    @pytest.mark.asyncio
    async def test_recall_last_week(self, populated_storage):
        """Test recalling memories from last week"""
        start_ts, end_ts = parse_time_expression("last week")
        results = await populated_storage.recall(
            query=None,
            n_results=10,
            start_timestamp=start_ts,
            end_timestamp=end_ts
        )
        
        # Should get last week's memories
        contents = [r.memory.content for r in results]
        assert any("Last" in c and "week" in ' '.join(r.memory.tags) for c, r in zip(contents, results))
    
    @pytest.mark.asyncio
    async def test_recall_with_semantic_and_time(self, populated_storage):
        """Test combined semantic and time-based recall"""
        # Extract time expression and search for "meeting" in last 10 days
        results = await populated_storage.recall(
            query="meeting",
            n_results=10,
            start_timestamp=time.time() - (10 * 24 * 3600),
            end_timestamp=time.time()
        )
        
        # Should find meetings within time range
        contents = [r.memory.content for r in results]
        assert any("meeting" in c.lower() for c in contents)
    
    @pytest.mark.asyncio
    async def test_recall_specific_date_range(self, populated_storage):
        """Test recall with specific date range"""
        # Query for January 2025
        start_ts = datetime(2025, 1, 1).timestamp()
        end_ts = datetime(2025, 1, 31, 23, 59, 59).timestamp()
        
        results = await populated_storage.recall(
            query=None,
            n_results=10,
            start_timestamp=start_ts,
            end_timestamp=end_ts
        )
        
        # Should find New Year memory
        contents = [r.memory.content for r in results]
        assert "New Year 2025" in contents
    
    @pytest.mark.asyncio  
    async def test_recall_time_of_day(self, populated_storage):
        """Test recall with time of day expressions"""
        # Get today's date at morning time
        today = date.today()
        morning_start = datetime.combine(today, datetime.min.time().replace(hour=5))
        morning_end = datetime.combine(today, datetime.min.time().replace(hour=11, minute=59, second=59))
        
        results = await populated_storage.recall(
            query=None,
            n_results=10,
            start_timestamp=morning_start.timestamp(),
            end_timestamp=morning_end.timestamp()
        )
        
        # Should find morning memories from today
        contents = [r.memory.content for r in results]
        assert any("morning" in c.lower() or "morning" in ' '.join(r.memory.tags) 
                  for c, r in zip(contents, results))
    
    @pytest.mark.asyncio
    async def test_edge_cases(self, storage):
        """Test edge cases for timestamp handling"""
        # Test with None timestamps
        results = await storage.recall(query="test", n_results=5)
        assert isinstance(results, list)
        
        # Test with very old timestamp
        old_time = datetime(1970, 1, 1).timestamp()
        memory = Memory(
            content="Very old memory",
            content_hash=generate_content_hash("Very old memory"),
            created_at=old_time
        )
        success, _ = await storage.store(memory)
        assert success
        
        # Test with future timestamp
        future_time = datetime(2030, 1, 1).timestamp()
        memory = Memory(
            content="Future memory",
            content_hash=generate_content_hash("Future memory"),
            created_at=future_time
        )
        success, _ = await storage.store(memory)
        assert success
    
    @pytest.mark.asyncio
    async def test_timestamp_normalization(self):
        """Test the normalize_timestamp function"""
        # Test with datetime object
        dt = datetime.now()
        normalized = ChromaMemoryStorage.normalize_timestamp(dt)
        assert isinstance(normalized, float)
        assert normalized == time.mktime(dt.timetuple())
        
        # Test with float
        ts = time.time()
        normalized = ChromaMemoryStorage.normalize_timestamp(ts)
        assert normalized == ts
        
        # Test with int
        ts_int = int(time.time())
        normalized = ChromaMemoryStorage.normalize_timestamp(ts_int)
        assert normalized == float(ts_int)


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])
