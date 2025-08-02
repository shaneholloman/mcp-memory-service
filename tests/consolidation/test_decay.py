"""Unit tests for the exponential decay calculator."""

import pytest
from datetime import datetime, timedelta

from mcp_memory_service.consolidation.decay import ExponentialDecayCalculator, RelevanceScore
from mcp_memory_service.models.memory import Memory


@pytest.mark.unit
class TestExponentialDecayCalculator:
    """Test the exponential decay scoring system."""
    
    @pytest.fixture
    def decay_calculator(self, consolidation_config):
        return ExponentialDecayCalculator(consolidation_config)
    
    @pytest.mark.asyncio
    async def test_basic_decay_calculation(self, decay_calculator, sample_memories):
        """Test basic decay calculation functionality."""
        memories = sample_memories[:3]  # Use first 3 memories
        
        scores = await decay_calculator.process(memories)
        
        assert len(scores) == 3
        assert all(isinstance(score, RelevanceScore) for score in scores)
        assert all(score.total_score > 0 for score in scores)
        assert all(0 <= score.decay_factor <= 1 for score in scores)
    
    @pytest.mark.asyncio
    async def test_memory_age_affects_decay(self, decay_calculator):
        """Test that older memories have lower decay factors."""
        now = datetime.now()
        
        # Create memories of different ages
        recent_time = now - timedelta(days=1)
        old_time = now - timedelta(days=30)
        
        recent_memory = Memory(
            content="Recent memory",
            content_hash="recent",
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=recent_time.timestamp(),
            created_at_iso=recent_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        )
        
        old_memory = Memory(
            content="Old memory",
            content_hash="old",
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=old_time.timestamp(),
            created_at_iso=old_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        )
        
        scores = await decay_calculator.process([recent_memory, old_memory])
        
        recent_score = next(s for s in scores if s.memory_hash == "recent")
        old_score = next(s for s in scores if s.memory_hash == "old")
        
        # Recent memory should have higher decay factor
        assert recent_score.decay_factor > old_score.decay_factor
        assert recent_score.total_score > old_score.total_score
    
    @pytest.mark.asyncio
    async def test_memory_type_affects_retention(self, decay_calculator):
        """Test that different memory types have different retention periods."""
        now = datetime.now()
        age_days = 60  # 2 months old
        
        # Create memories of different types but same age
        critical_memory = Memory(
            content="Critical memory",
            content_hash="critical",
            tags=["critical"],
            memory_type="critical",
            embedding=[0.1] * 320,
            created_at=(now - timedelta(days=age_days)).timestamp(),
            created_at_iso=(now - timedelta(days=age_days)).isoformat() + 'Z'
        )
        
        temporary_memory = Memory(
            content="Temporary memory",
            content_hash="temporary",
            tags=["temp"],
            memory_type="temporary",
            embedding=[0.1] * 320,
            created_at=(now - timedelta(days=age_days)).timestamp(),
            created_at_iso=(now - timedelta(days=age_days)).isoformat() + 'Z'
        )
        
        scores = await decay_calculator.process([critical_memory, temporary_memory])
        
        critical_score = next(s for s in scores if s.memory_hash == "critical")
        temp_score = next(s for s in scores if s.memory_hash == "temporary")
        
        # Critical memory should decay slower (higher decay factor)
        assert critical_score.decay_factor > temp_score.decay_factor
        assert critical_score.metadata['retention_period'] > temp_score.metadata['retention_period']
    
    @pytest.mark.asyncio
    async def test_connections_boost_relevance(self, decay_calculator):
        """Test that memories with connections get relevance boost."""
        memory = Memory(
            content="Connected memory",
            content_hash="connected",
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )
        
        # Test with no connections
        scores_no_connections = await decay_calculator.process(
            [memory], 
            connections={}
        )
        
        # Test with connections
        scores_with_connections = await decay_calculator.process(
            [memory],
            connections={"connected": 3}
        )
        
        no_conn_score = scores_no_connections[0]
        with_conn_score = scores_with_connections[0]
        
        assert with_conn_score.connection_boost > no_conn_score.connection_boost
        assert with_conn_score.total_score > no_conn_score.total_score
        assert with_conn_score.metadata['connection_count'] == 3
    
    @pytest.mark.asyncio
    async def test_access_patterns_boost_relevance(self, decay_calculator):
        """Test that recent access boosts relevance."""
        memory = Memory(
            content="Accessed memory",
            content_hash="accessed",
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )
        
        # Test with no recent access
        scores_no_access = await decay_calculator.process([memory])
        
        # Test with recent access
        recent_access = {
            "accessed": datetime.now() - timedelta(hours=6)
        }
        scores_recent_access = await decay_calculator.process(
            [memory],
            access_patterns=recent_access
        )
        
        no_access_score = scores_no_access[0]
        recent_access_score = scores_recent_access[0]
        
        assert recent_access_score.access_boost > no_access_score.access_boost
        assert recent_access_score.total_score > no_access_score.total_score
    
    @pytest.mark.asyncio
    async def test_base_importance_from_metadata(self, decay_calculator):
        """Test that explicit importance scores are used."""
        high_importance_memory = Memory(
            content="Important memory",
            content_hash="important",
            tags=["test"],
            embedding=[0.1] * 320,
            metadata={"importance_score": 1.8},
            created_at=datetime.now().timestamp()
        )
        
        normal_memory = Memory(
            content="Normal memory",
            content_hash="normal", 
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )
        
        scores = await decay_calculator.process([high_importance_memory, normal_memory])
        
        important_score = next(s for s in scores if s.memory_hash == "important")
        normal_score = next(s for s in scores if s.memory_hash == "normal")
        
        assert important_score.base_importance > normal_score.base_importance
        assert important_score.total_score > normal_score.total_score
    
    @pytest.mark.asyncio
    async def test_base_importance_from_tags(self, decay_calculator):
        """Test that importance is derived from tags."""
        critical_memory = Memory(
            content="Critical memory",
            content_hash="critical_tag",
            tags=["critical", "system"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )
        
        temp_memory = Memory(
            content="Temporary memory",
            content_hash="temp_tag",
            tags=["temporary", "draft"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )
        
        scores = await decay_calculator.process([critical_memory, temp_memory])
        
        critical_score = next(s for s in scores if s.memory_hash == "critical_tag")
        temp_score = next(s for s in scores if s.memory_hash == "temp_tag")
        
        assert critical_score.base_importance > temp_score.base_importance
    
    @pytest.mark.asyncio
    async def test_protected_memory_minimum_relevance(self, decay_calculator):
        """Test that protected memories maintain minimum relevance."""
        # Create a very old memory that would normally have very low relevance
        old_critical_memory = Memory(
            content="Old critical memory",
            content_hash="old_critical",
            tags=["critical", "important"],
            memory_type="critical",
            embedding=[0.1] * 320,
            created_at=(datetime.now() - timedelta(days=500)).timestamp(),
            created_at_iso=(datetime.now() - timedelta(days=500)).isoformat() + 'Z'
        )
        
        scores = await decay_calculator.process([old_critical_memory])
        score = scores[0]
        
        # Even very old critical memory should maintain minimum relevance
        assert score.total_score >= 0.5  # Minimum for protected memories
        assert score.metadata['is_protected'] is True
    
    @pytest.mark.asyncio
    async def test_get_low_relevance_memories(self, decay_calculator, sample_memories):
        """Test filtering of low relevance memories."""
        scores = await decay_calculator.process(sample_memories)
        
        low_relevance = await decay_calculator.get_low_relevance_memories(scores, threshold=0.5)
        
        # Should find some low relevance memories
        assert len(low_relevance) > 0
        assert all(score.total_score < 0.5 for score in low_relevance)
    
    @pytest.mark.asyncio
    async def test_get_high_relevance_memories(self, decay_calculator, sample_memories):
        """Test filtering of high relevance memories."""
        scores = await decay_calculator.process(sample_memories)
        
        high_relevance = await decay_calculator.get_high_relevance_memories(scores, threshold=1.0)
        
        # Should find some high relevance memories  
        assert len(high_relevance) >= 0
        assert all(score.total_score >= 1.0 for score in high_relevance)
    
    @pytest.mark.asyncio
    async def test_update_memory_relevance_metadata(self, decay_calculator):
        """Test updating memory with relevance metadata."""
        memory = Memory(
            content="Test memory",
            content_hash="test",
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )
        
        scores = await decay_calculator.process([memory])
        score = scores[0]
        
        updated_memory = await decay_calculator.update_memory_relevance_metadata(memory, score)
        
        assert 'relevance_score' in updated_memory.metadata
        assert 'relevance_calculated_at' in updated_memory.metadata
        assert 'decay_factor' in updated_memory.metadata
        assert 'connection_boost' in updated_memory.metadata
        assert 'access_boost' in updated_memory.metadata
        assert updated_memory.metadata['relevance_score'] == score.total_score
    
    @pytest.mark.asyncio
    async def test_empty_memories_list(self, decay_calculator):
        """Test handling of empty memories list."""
        scores = await decay_calculator.process([])
        assert scores == []
    
    @pytest.mark.asyncio
    async def test_memory_without_embedding(self, decay_calculator):
        """Test handling of memory without embedding."""
        memory = Memory(
            content="No embedding",
            content_hash="no_embedding",
            tags=["test"],
            embedding=None,  # No embedding
            created_at=datetime.now().timestamp()
        )
        
        scores = await decay_calculator.process([memory])
        
        # Should still work, just without embedding-based features
        assert len(scores) == 1
        assert scores[0].total_score > 0