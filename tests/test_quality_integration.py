"""Integration tests for quality-based consolidation and search."""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import List

from mcp_memory_service.consolidation.forgetting import ControlledForgettingEngine
from mcp_memory_service.consolidation.decay import ExponentialDecayCalculator, RelevanceScore
from mcp_memory_service.consolidation.base import ConsolidationConfig
from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.models.memory import Memory
from mcp_memory_service.config import (
    MCP_QUALITY_RETENTION_HIGH,
    MCP_QUALITY_RETENTION_MEDIUM,
    MCP_QUALITY_RETENTION_LOW_MIN,
    MCP_QUALITY_RETENTION_LOW_MAX,
)


@pytest.fixture
async def storage():
    """Create an in-memory SQLite storage instance."""
    storage = SqliteVecMemoryStorage(':memory:')
    await storage.initialize()
    yield storage
    # Cleanup is automatic for in-memory database


def create_memory(content: str, quality_score: float = 0.5, days_old: int = 0, tags: List[str] = None) -> Memory:
    """Helper to create a memory with specified quality and age."""
    created_at = time.time() - (days_old * 86400)
    memory = Memory(
        content=content,
        content_hash=f"hash_{hash(content)}",
        tags=tags or [],
        metadata={'quality_score': quality_score},
        created_at=created_at,
        created_at_iso=datetime.fromtimestamp(created_at).isoformat() + 'Z'
    )
    return memory


@pytest.mark.asyncio
async def test_quality_based_forgetting():
    """Test that high-quality memories are preserved longer."""
    config = ConsolidationConfig(
        relevance_threshold=0.1,
        access_threshold_days=90,
        archive_location='/tmp/test_archive'
    )
    forgetting_engine = ControlledForgettingEngine(config)

    # Create memories with different quality scores and ages
    high_quality_old = create_memory("High quality old memory", quality_score=0.9, days_old=200)
    medium_quality_old = create_memory("Medium quality old memory", quality_score=0.6, days_old=200)
    low_quality_old = create_memory("Low quality old memory", quality_score=0.2, days_old=60)

    memories = [high_quality_old, medium_quality_old, low_quality_old]

    # Create relevance scores (all with low total_score to trigger forgetting check)
    score_lookup = {
        high_quality_old.content_hash: RelevanceScore(
            memory_hash=high_quality_old.content_hash,
            total_score=0.5,
            base_importance=1.0,
            decay_factor=0.5,
            connection_boost=1.0,
            access_boost=1.0,
            metadata={}
        ),
        medium_quality_old.content_hash: RelevanceScore(
            memory_hash=medium_quality_old.content_hash,
            total_score=0.5,
            base_importance=1.0,
            decay_factor=0.5,
            connection_boost=1.0,
            access_boost=1.0,
            metadata={}
        ),
        low_quality_old.content_hash: RelevanceScore(
            memory_hash=low_quality_old.content_hash,
            total_score=0.5,
            base_importance=1.0,
            decay_factor=0.5,
            connection_boost=1.0,
            access_boost=1.0,
            metadata={}
        ),
    }

    # Set access patterns (simulate old access)
    access_patterns = {
        high_quality_old.content_hash: datetime.now() - timedelta(days=200),
        medium_quality_old.content_hash: datetime.now() - timedelta(days=200),
        low_quality_old.content_hash: datetime.now() - timedelta(days=60),
    }

    # Identify forgetting candidates
    candidates = await forgetting_engine._identify_forgetting_candidates(
        memories, score_lookup, access_patterns, 'monthly'
    )

    # Verify quality-based retention policy
    candidate_hashes = {c.memory.content_hash for c in candidates}

    # High quality (0.9): 200 days < 365 day threshold -> should NOT be candidate
    assert high_quality_old.content_hash not in candidate_hashes, \
        "High quality memory should be preserved longer"

    # Medium quality (0.6): 200 days > 180 day threshold -> should be candidate
    assert medium_quality_old.content_hash in candidate_hashes, \
        "Medium quality memory should be candidate after 180 days"

    # Low quality (0.2): 60 days > scaled threshold (30 + 0.4*60 = 54 days) -> should be candidate
    assert low_quality_old.content_hash in candidate_hashes, \
        "Low quality memory should be candidate after short period"


@pytest.mark.asyncio
async def test_quality_weighted_decay():
    """Test that high-quality memories have slower decay."""
    config = ConsolidationConfig(
        retention_periods={'standard': 30}
    )
    decay_calculator = ExponentialDecayCalculator(config)

    # Create memories with different quality scores
    high_quality = create_memory("High quality memory", quality_score=0.9, days_old=10)
    low_quality = create_memory("Low quality memory", quality_score=0.2, days_old=10)

    # Calculate decay scores
    high_score = await decay_calculator._calculate_memory_relevance(
        high_quality,
        datetime.now(),
        {},  # no connections
        {}   # no access patterns
    )

    low_score = await decay_calculator._calculate_memory_relevance(
        low_quality,
        datetime.now(),
        {},  # no connections
        {}   # no access patterns
    )

    # High quality should have higher total score due to quality multiplier
    assert high_score.total_score > low_score.total_score, \
        "High quality memory should have slower decay (higher score)"

    # Verify quality multiplier is applied
    assert 'quality_multiplier' in high_score.metadata
    assert 'quality_multiplier' in low_score.metadata
    assert high_score.metadata['quality_multiplier'] > low_score.metadata['quality_multiplier']


@pytest.mark.asyncio
async def test_quality_boosted_search(storage):
    """Test quality-based reranking improves results."""
    # Store memories with varying quality and semantic similarity
    # Memory 1: High semantic relevance, low quality
    mem1 = create_memory(
        "Python async patterns for concurrent programming with asyncio",
        quality_score=0.3,
        tags=['python', 'async']
    )

    # Memory 2: Medium semantic relevance, high quality
    mem2 = create_memory(
        "Advanced Python concurrency techniques",
        quality_score=0.9,
        tags=['python', 'advanced']
    )

    # Memory 3: Low semantic relevance, medium quality
    mem3 = create_memory(
        "JavaScript promises and callbacks",
        quality_score=0.5,
        tags=['javascript']
    )

    await storage.store(mem1)
    await storage.store(mem2)
    await storage.store(mem3)

    # Search with quality boost disabled (semantic only)
    semantic_results = await storage.retrieve_with_quality_boost(
        query="Python async programming",
        n_results=3,
        quality_boost=False
    )

    # Search with quality boost enabled (70% semantic + 30% quality)
    boosted_results = await storage.retrieve_with_quality_boost(
        query="Python async programming",
        n_results=3,
        quality_boost=True,
        quality_weight=0.3
    )

    # Verify reranking occurred
    assert len(boosted_results) > 0
    for result in boosted_results:
        assert 'reranked' in result.debug_info
        assert result.debug_info['reranked'] is True
        assert 'original_semantic_score' in result.debug_info
        assert 'quality_score' in result.debug_info


@pytest.mark.asyncio
async def test_quality_boost_performance(storage):
    """Test that quality boost doesn't add excessive latency."""
    # Store 100 memories with random quality scores
    import random
    for i in range(100):
        memory = create_memory(
            f"Test memory {i} with some content about Python and async patterns",
            quality_score=random.random(),
            tags=['test', f'batch-{i//10}']
        )
        await storage.store(memory)

    # Measure latency
    start = time.time()
    results = await storage.retrieve_with_quality_boost(
        query="Python async",
        n_results=10,
        quality_boost=True,
        quality_weight=0.3
    )
    latency = time.time() - start

    # Should be fast (<200ms target for 100 memories)
    assert latency < 0.2, f"Quality boost too slow: {latency:.3f}s"
    assert len(results) <= 10


@pytest.mark.asyncio
async def test_quality_boost_weight_validation(storage):
    """Test that invalid quality weights are rejected."""
    memory = create_memory("Test memory", quality_score=0.5)
    await storage.store(memory)

    # Test invalid weight (too high)
    with pytest.raises(ValueError, match="quality_weight must be 0.0-1.0"):
        await storage.retrieve_with_quality_boost(
            query="test",
            n_results=5,
            quality_boost=True,
            quality_weight=1.5
        )

    # Test invalid weight (negative)
    with pytest.raises(ValueError, match="quality_weight must be 0.0-1.0"):
        await storage.retrieve_with_quality_boost(
            query="test",
            n_results=5,
            quality_boost=True,
            quality_weight=-0.1
        )


@pytest.mark.asyncio
async def test_quality_boost_edge_cases(storage):
    """Test quality boost with edge cases."""
    # Test with no memories
    results = await storage.retrieve_with_quality_boost(
        query="nonexistent",
        n_results=10,
        quality_boost=True
    )
    assert len(results) == 0

    # Test with single memory
    memory = create_memory("Single memory", quality_score=0.7)
    await storage.store(memory)

    results = await storage.retrieve_with_quality_boost(
        query="single",
        n_results=10,
        quality_boost=True
    )
    assert len(results) == 1

    # Test with quality_weight=0.0 (semantic only)
    results = await storage.retrieve_with_quality_boost(
        query="single",
        n_results=10,
        quality_boost=True,
        quality_weight=0.0
    )
    assert len(results) == 1

    # Test with quality_weight=1.0 (quality only)
    results = await storage.retrieve_with_quality_boost(
        query="single",
        n_results=10,
        quality_boost=True,
        quality_weight=1.0
    )
    assert len(results) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
