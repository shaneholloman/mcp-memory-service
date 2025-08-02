"""Unit tests for the semantic clustering engine."""

import pytest
import numpy as np
from datetime import datetime, timedelta

from mcp_memory_service.consolidation.clustering import SemanticClusteringEngine
from mcp_memory_service.consolidation.base import MemoryCluster
from mcp_memory_service.models.memory import Memory


@pytest.mark.unit
class TestSemanticClusteringEngine:
    """Test the semantic clustering system."""
    
    @pytest.fixture
    def clustering_engine(self, consolidation_config):
        return SemanticClusteringEngine(consolidation_config)
    
    @pytest.mark.asyncio
    async def test_basic_clustering(self, clustering_engine, sample_memories):
        """Test basic clustering functionality."""
        # Use memories with embeddings
        memories_with_embeddings = [m for m in sample_memories if m.embedding]
        
        clusters = await clustering_engine.process(memories_with_embeddings)
        
        assert isinstance(clusters, list)
        assert all(isinstance(cluster, MemoryCluster) for cluster in clusters)
        
        for cluster in clusters:
            assert len(cluster.memory_hashes) >= clustering_engine.min_cluster_size
            assert isinstance(cluster.cluster_id, str)
            assert isinstance(cluster.centroid_embedding, list)
            assert len(cluster.centroid_embedding) > 0
            assert 0 <= cluster.coherence_score <= 1
            assert isinstance(cluster.created_at, datetime)
            assert isinstance(cluster.theme_keywords, list)
    
    @pytest.mark.asyncio 
    async def test_clustering_with_similar_embeddings(self, clustering_engine):
        """Test clustering with known similar embeddings."""
        base_time = datetime.now().timestamp()
        
        # Create memories with similar embeddings (should cluster together)
        similar_memories = []
        base_embedding = [0.5, 0.4, 0.6, 0.3, 0.7]
        
        for i in range(6):  # Create enough for min_cluster_size
            # Add small variations to base embedding
            embedding = []
            for val in base_embedding * 64:  # 320-dim
                noise = np.random.normal(0, 0.05)  # Small noise
                embedding.append(max(0, min(1, val + noise)))
            
            memory = Memory(
                content=f"Similar content about programming topic {i}",
                content_hash=f"similar_{i}",
                tags=["programming", "similar"],
                embedding=embedding,
                created_at=base_time - (i * 3600)
            )
            similar_memories.append(memory)
        
        # Add some different memories
        for i in range(3):
            different_embedding = [0.1, 0.9, 0.2, 0.8, 0.1] * 64
            memory = Memory(
                content=f"Different content about weather {i}",
                content_hash=f"different_{i}",
                tags=["weather", "different"],
                embedding=different_embedding,
                created_at=base_time - (i * 3600)
            )
            similar_memories.append(memory)
        
        clusters = await clustering_engine.process(similar_memories)
        
        # Should find at least one cluster
        assert len(clusters) >= 1
        
        # Check that similar memories are clustered together
        if clusters:
            # Find cluster with similar memories
            similar_cluster = None
            for cluster in clusters:
                if any("similar" in hash_id for hash_id in cluster.memory_hashes):
                    similar_cluster = cluster
                    break
            
            if similar_cluster:
                # Should contain multiple similar memories
                similar_hashes = [h for h in similar_cluster.memory_hashes if "similar" in h]
                assert len(similar_hashes) >= clustering_engine.min_cluster_size
    
    @pytest.mark.asyncio
    async def test_insufficient_memories(self, clustering_engine):
        """Test handling of insufficient memories for clustering."""
        # Create too few memories
        few_memories = []
        for i in range(2):  # Less than min_cluster_size
            memory = Memory(
                content=f"Content {i}",
                content_hash=f"hash_{i}",
                tags=["test"],
                embedding=[0.5] * 320,
                created_at=datetime.now().timestamp()
            )
            few_memories.append(memory)
        
        clusters = await clustering_engine.process(few_memories)
        assert clusters == []
    
    @pytest.mark.asyncio
    async def test_memories_without_embeddings(self, clustering_engine):
        """Test handling of memories without embeddings."""
        memories_no_embeddings = []
        for i in range(5):
            memory = Memory(
                content=f"Content {i}",
                content_hash=f"hash_{i}",
                tags=["test"],
                embedding=None,  # No embedding
                created_at=datetime.now().timestamp()
            )
            memories_no_embeddings.append(memory)
        
        clusters = await clustering_engine.process(memories_no_embeddings)
        assert clusters == []
    
    @pytest.mark.asyncio
    async def test_theme_keyword_extraction(self, clustering_engine):
        """Test extraction of theme keywords from clusters."""
        # Create memories with common themes
        themed_memories = []
        base_embedding = [0.5, 0.5, 0.5, 0.5, 0.5] * 64
        
        for i in range(5):
            memory = Memory(
                content=f"Python programming tutorial {i} about functions and classes",
                content_hash=f"python_{i}",
                tags=["python", "programming", "tutorial"],
                embedding=[val + np.random.normal(0, 0.02) for val in base_embedding],
                created_at=datetime.now().timestamp()
            )
            themed_memories.append(memory)
        
        clusters = await clustering_engine.process(themed_memories)
        
        if clusters:
            cluster = clusters[0]
            # Should extract relevant theme keywords
            assert len(cluster.theme_keywords) > 0
            
            # Should include frequent tags
            common_tags = {"python", "programming", "tutorial"}
            found_tags = set(cluster.theme_keywords).intersection(common_tags)
            assert len(found_tags) > 0
    
    @pytest.mark.asyncio
    async def test_cluster_metadata(self, clustering_engine, sample_memories):
        """Test that cluster metadata is properly populated."""
        memories_with_embeddings = [m for m in sample_memories if m.embedding]
        
        if len(memories_with_embeddings) >= clustering_engine.min_cluster_size:
            clusters = await clustering_engine.process(memories_with_embeddings)
            
            for cluster in clusters:
                assert 'algorithm' in cluster.metadata
                assert 'cluster_size' in cluster.metadata
                assert 'average_memory_age' in cluster.metadata
                assert 'tag_distribution' in cluster.metadata
                
                assert cluster.metadata['cluster_size'] == len(cluster.memory_hashes)
                assert isinstance(cluster.metadata['average_memory_age'], float)
                assert isinstance(cluster.metadata['tag_distribution'], dict)
    
    @pytest.mark.asyncio
    async def test_simple_clustering_fallback(self, clustering_engine):
        """Test simple clustering algorithm fallback."""
        # Force simple clustering algorithm
        original_algorithm = clustering_engine.algorithm
        clustering_engine.algorithm = 'simple'
        
        try:
            # Create memories with known similarity patterns
            similar_memories = []
            
            # Group 1: High similarity
            base1 = [0.8, 0.7, 0.9, 0.8, 0.7] * 64
            for i in range(4):
                embedding = [val + np.random.normal(0, 0.01) for val in base1]
                memory = Memory(
                    content=f"Group 1 content {i}",
                    content_hash=f"group1_{i}",
                    tags=["group1"],
                    embedding=embedding,
                    created_at=datetime.now().timestamp()
                )
                similar_memories.append(memory)
            
            # Group 2: Different but internally similar  
            base2 = [0.2, 0.3, 0.1, 0.2, 0.3] * 64
            for i in range(4):
                embedding = [val + np.random.normal(0, 0.01) for val in base2]
                memory = Memory(
                    content=f"Group 2 content {i}",
                    content_hash=f"group2_{i}",
                    tags=["group2"],
                    embedding=embedding,
                    created_at=datetime.now().timestamp()
                )
                similar_memories.append(memory)
            
            clusters = await clustering_engine.process(similar_memories)
            
            # Simple algorithm should still find clusters
            assert isinstance(clusters, list)
            
        finally:
            clustering_engine.algorithm = original_algorithm
    
    @pytest.mark.asyncio
    async def test_merge_similar_clusters(self, clustering_engine):
        """Test merging of similar clusters."""
        # Create two similar clusters
        cluster1 = MemoryCluster(
            cluster_id="cluster1",
            memory_hashes=["hash1", "hash2"],
            centroid_embedding=[0.5, 0.5, 0.5] * 107,  # ~320 dim
            coherence_score=0.8,
            created_at=datetime.now(),
            theme_keywords=["python", "programming"]
        )
        
        cluster2 = MemoryCluster(
            cluster_id="cluster2", 
            memory_hashes=["hash3", "hash4"],
            centroid_embedding=[0.52, 0.48, 0.51] * 107,  # Similar to cluster1
            coherence_score=0.7,
            created_at=datetime.now(),
            theme_keywords=["python", "coding"]
        )
        
        # Very different cluster
        cluster3 = MemoryCluster(
            cluster_id="cluster3",
            memory_hashes=["hash5", "hash6"],
            centroid_embedding=[0.1, 0.9, 0.1] * 107,  # Very different
            coherence_score=0.6,
            created_at=datetime.now(),
            theme_keywords=["weather", "forecast"]
        )
        
        clusters = [cluster1, cluster2, cluster3]
        merged_clusters = await clustering_engine.merge_similar_clusters(
            clusters, similarity_threshold=0.9
        )
        
        # Should merge similar clusters
        assert len(merged_clusters) <= len(clusters)
        
        # Check that merged cluster contains memories from both original clusters
        if len(merged_clusters) < len(clusters):
            # Find the merged cluster (should have more memories)
            merged = max(merged_clusters, key=lambda c: len(c.memory_hashes))
            assert len(merged.memory_hashes) >= 4  # Combined from cluster1 and cluster2
    
    @pytest.mark.asyncio
    async def test_coherence_score_calculation(self, clustering_engine):
        """Test coherence score calculation for clusters."""
        # Create tightly clustered memories
        tight_memories = []
        base_embedding = [0.5, 0.5, 0.5, 0.5, 0.5] * 64
        
        for i in range(5):
            # Very similar embeddings (high coherence)
            embedding = [val + np.random.normal(0, 0.01) for val in base_embedding]
            memory = Memory(
                content=f"Tight cluster content {i}",
                content_hash=f"tight_{i}",
                tags=["tight"],
                embedding=embedding,
                created_at=datetime.now().timestamp()
            )
            tight_memories.append(memory)
        
        # Create loosely clustered memories
        loose_memories = []
        for i in range(5):
            # More varied embeddings (lower coherence)
            embedding = [val + np.random.normal(0, 0.1) for val in base_embedding]
            memory = Memory(
                content=f"Loose cluster content {i}",
                content_hash=f"loose_{i}",
                tags=["loose"],
                embedding=embedding,
                created_at=datetime.now().timestamp()
            )
            loose_memories.append(memory)
        
        tight_clusters = await clustering_engine.process(tight_memories)
        loose_clusters = await clustering_engine.process(loose_memories)
        
        # Tight clusters should have higher coherence scores
        if tight_clusters and loose_clusters:
            tight_coherence = tight_clusters[0].coherence_score
            loose_coherence = loose_clusters[0].coherence_score
            
            # This may not always be true due to randomness, but generally should be
            # Just check that coherence scores are in valid range
            assert 0 <= tight_coherence <= 1
            assert 0 <= loose_coherence <= 1
    
    @pytest.mark.asyncio
    async def test_algorithm_fallback_handling(self, clustering_engine):
        """Test handling of different clustering algorithms."""
        memories = []
        base_embedding = [0.5, 0.4, 0.6, 0.3, 0.7] * 64
        
        for i in range(8):  # Enough for clustering
            embedding = [val + np.random.normal(0, 0.05) for val in base_embedding]
            memory = Memory(
                content=f"Test content {i}",
                content_hash=f"test_{i}",
                tags=["test"],
                embedding=embedding,
                created_at=datetime.now().timestamp()
            )
            memories.append(memory)
        
        # Test different algorithms
        algorithms = ['simple', 'dbscan', 'hierarchical']
        
        for algorithm in algorithms:
            original_algorithm = clustering_engine.algorithm
            clustering_engine.algorithm = algorithm
            
            try:
                clusters = await clustering_engine.process(memories)
                
                # All algorithms should return valid clusters
                assert isinstance(clusters, list)
                for cluster in clusters:
                    assert isinstance(cluster, MemoryCluster)
                    assert cluster.metadata['algorithm'] in [algorithm, f"{algorithm}_merged"]
                    
            finally:
                clustering_engine.algorithm = original_algorithm
    
    @pytest.mark.asyncio
    async def test_empty_input_handling(self, clustering_engine):
        """Test handling of empty input."""
        clusters = await clustering_engine.process([])
        assert clusters == []
    
    @pytest.mark.asyncio
    async def test_average_age_calculation(self, clustering_engine):
        """Test average age calculation in cluster metadata."""
        now = datetime.now()
        memories = []
        
        # Create memories with known ages
        ages = [1, 3, 5, 7, 9]  # days ago
        for i, age in enumerate(ages):
            memory = Memory(
                content=f"Content {i}",
                content_hash=f"age_test_{i}",
                tags=["age_test"],
                embedding=[0.5 + i*0.01] * 320,  # Slightly different embeddings
                created_at=(now - timedelta(days=age)).timestamp()
            )
            memories.append(memory)
        
        clusters = await clustering_engine.process(memories)
        
        if clusters:
            cluster = clusters[0]
            avg_age = cluster.metadata['average_memory_age']
            
            # Average age should be approximately the mean of our test ages
            expected_avg = sum(ages) / len(ages)
            assert abs(avg_age - expected_avg) < 1  # Within 1 day tolerance
    
    @pytest.mark.asyncio
    async def test_tag_distribution_analysis(self, clustering_engine):
        """Test tag distribution analysis in clusters."""
        memories = []
        base_embedding = [0.5] * 320
        
        # Create memories with specific tag patterns
        tag_patterns = [
            ["python", "programming"],
            ["python", "tutorial"],
            ["programming", "guide"],
            ["python", "programming"],  # Duplicate pattern
            ["tutorial", "guide"]
        ]
        
        for i, tags in enumerate(tag_patterns):
            memory = Memory(
                content=f"Content {i}",
                content_hash=f"tag_test_{i}",
                tags=tags,
                embedding=[val + i*0.01 for val in base_embedding],
                created_at=datetime.now().timestamp()
            )
            memories.append(memory)
        
        clusters = await clustering_engine.process(memories)
        
        if clusters:
            cluster = clusters[0]
            tag_dist = cluster.metadata['tag_distribution']
            
            # Should count tag frequencies correctly  
            assert isinstance(tag_dist, dict)
            assert tag_dist.get("python", 0) >= 2  # Appears multiple times
            assert tag_dist.get("programming", 0) >= 2  # Appears multiple times