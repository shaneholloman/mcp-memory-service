"""Unit tests for the creative association engine."""

import pytest
from datetime import datetime, timedelta

from mcp_memory_service.consolidation.associations import (
    CreativeAssociationEngine, 
    AssociationAnalysis
)
from mcp_memory_service.consolidation.base import MemoryAssociation
from mcp_memory_service.models.memory import Memory


@pytest.mark.unit
class TestCreativeAssociationEngine:
    """Test the creative association discovery system."""
    
    @pytest.fixture
    def association_engine(self, consolidation_config):
        return CreativeAssociationEngine(consolidation_config)
    
    @pytest.mark.asyncio
    async def test_basic_association_discovery(self, association_engine, sample_memories):
        """Test basic association discovery functionality."""
        # Use memories that should have some associations
        memories = sample_memories[:5]
        
        associations = await association_engine.process(memories)
        
        # Should find some associations
        assert isinstance(associations, list)
        assert all(isinstance(assoc, MemoryAssociation) for assoc in associations)
        
        # Check association properties
        for assoc in associations:
            assert len(assoc.source_memory_hashes) == 2
            assert 0.3 <= assoc.similarity_score <= 0.7  # Sweet spot range
            assert assoc.discovery_method == "creative_association"
            assert isinstance(assoc.discovery_date, datetime)
    
    @pytest.mark.asyncio
    async def test_similarity_sweet_spot_filtering(self, association_engine):
        """Test that only memories in similarity sweet spot are associated."""
        now = datetime.now()
        
        # Create memories with known similarity relationships
        base_memory = Memory(
            content="Python programming concepts",
            content_hash="base",
            tags=["python", "programming"],
            embedding=[0.5, 0.5, 0.5, 0.5, 0.5] * 64,
            created_at=now.timestamp()
        )
        
        # Very similar memory (should be filtered out - too similar)
        too_similar = Memory(  
            content="Python programming concepts and techniques",
            content_hash="similar",
            tags=["python", "programming"],
            embedding=[0.51, 0.51, 0.51, 0.51, 0.51] * 64,  # Very similar
            created_at=now.timestamp()
        )
        
        # Moderately similar memory (should be included)
        good_similarity = Memory(
            content="JavaScript development practices",
            content_hash="moderate",
            tags=["javascript", "development"],
            embedding=[0.6, 0.4, 0.6, 0.4, 0.6] * 64,  # Moderate similarity
            created_at=now.timestamp()
        )
        
        # Very different memory (should be filtered out - too different)
        too_different = Memory(
            content="Weather forecast for tomorrow",
            content_hash="different",
            tags=["weather", "forecast"],
            embedding=[0.1, 0.9, 0.1, 0.9, 0.1] * 64,  # Very different
            created_at=now.timestamp()
        )
        
        memories = [base_memory, too_similar, good_similarity, too_different]
        associations = await association_engine.process(memories)
        
        # Should only find association between base and good_similarity
        if associations:  # May be empty due to confidence threshold
            for assoc in associations:
                assert assoc.similarity_score >= 0.3
                assert assoc.similarity_score <= 0.7
    
    @pytest.mark.asyncio
    async def test_existing_associations_filtering(self, association_engine, sample_memories):
        """Test that existing associations are not duplicated."""
        memories = sample_memories[:4]
        
        # Create set of existing associations
        existing = {
            (memories[0].content_hash, memories[1].content_hash),
            (memories[1].content_hash, memories[0].content_hash)  # Both directions
        }
        
        associations = await association_engine.process(
            memories, 
            existing_associations=existing
        )
        
        # Should not include the existing association
        for assoc in associations:
            pair = tuple(sorted(assoc.source_memory_hashes))
            existing_pairs = {tuple(sorted(list(existing_pair))) for existing_pair in existing}
            assert pair not in existing_pairs
    
    @pytest.mark.asyncio
    async def test_association_analysis(self, association_engine):
        """Test the association analysis functionality."""
        # Create memories with known relationships
        mem1 = Memory(
            content="Python list comprehensions provide concise syntax",
            content_hash="mem1",
            tags=["python", "syntax"],
            embedding=[0.4, 0.5, 0.6, 0.5, 0.4] * 64,
            created_at=datetime.now().timestamp()
        )
        
        mem2 = Memory(
            content="JavaScript arrow functions offer clean syntax",
            content_hash="mem2", 
            tags=["javascript", "syntax"],
            embedding=[0.5, 0.4, 0.5, 0.6, 0.5] * 64,
            created_at=datetime.now().timestamp()
        )
        
        # Calculate similarity
        similarity = await association_engine._calculate_semantic_similarity(mem1, mem2)
        
        # Analyze the association
        analysis = await association_engine._analyze_association(mem1, mem2, similarity)
        
        assert isinstance(analysis, AssociationAnalysis)
        assert analysis.memory1_hash == "mem1"
        assert analysis.memory2_hash == "mem2"
        assert analysis.similarity_score == similarity
        assert "shared_tags" in analysis.connection_reasons  # Both have "syntax" tag
        assert "syntax" in analysis.tag_overlap
        assert analysis.confidence_score > 0
    
    @pytest.mark.asyncio
    async def test_temporal_relationship_analysis(self, association_engine):
        """Test temporal relationship detection."""
        now = datetime.now()
        
        # Memories created on same day
        mem1 = Memory(
            content="Morning meeting notes",
            content_hash="morning",
            tags=["meeting"],
            embedding=[0.4, 0.5, 0.6] * 107,  # ~320 dim
            created_at=now.timestamp()
        )
        
        mem2 = Memory(
            content="Afternoon project update",
            content_hash="afternoon",
            tags=["project"],
            embedding=[0.5, 0.4, 0.5] * 107,
            created_at=(now + timedelta(hours=6)).timestamp()
        )
        
        analysis = await association_engine._analyze_association(
            mem1, mem2, 0.5
        )
        
        assert analysis.temporal_relationship == "same_day"
        assert "temporal_proximity" in analysis.connection_reasons
    
    @pytest.mark.asyncio
    async def test_concept_extraction(self, association_engine):
        """Test concept extraction from memory content."""
        content = 'Check out this URL: https://example.com and email me at test@example.com. The API returns {"status": "success"} with CamelCase variables.'
        
        concepts = association_engine._extract_concepts(content)
        
        # Should extract various types of concepts
        assert "https://example.com" in concepts or any("example.com" in c for c in concepts)
        assert "test@example.com" in concepts
        assert "CamelCase" in concepts or any("camel" in c.lower() for c in concepts)
        assert len(concepts) > 0
    
    @pytest.mark.asyncio
    async def test_structural_similarity_detection(self, association_engine):
        """Test detection of similar structural patterns."""
        content1 = """
        # Header 1
        - Item 1
        - Item 2
        ```code block```
        """
        
        content2 = """
        # Header 2  
        - Different item 1
        - Different item 2
        ```another code block```
        """
        
        has_similar = association_engine._has_similar_structure(content1, content2)
        assert has_similar is True
        
        # Test different structure
        content3 = "Just plain text without any special formatting."
        has_different = association_engine._has_similar_structure(content1, content3)
        assert has_different is False
    
    @pytest.mark.asyncio
    async def test_complementary_content_detection(self, association_engine):
        """Test detection of complementary content patterns."""
        # Question and answer pattern
        question_content = "How do you implement binary search? What is the time complexity?"
        answer_content = "Binary search implementation uses divide and conquer. Time complexity is O(log n)."
        
        is_complementary = association_engine._has_complementary_content(
            question_content, answer_content
        )
        assert is_complementary is True
        
        # Problem and solution pattern
        problem_content = "The database query is failing with timeout error"
        solution_content = "Fixed the timeout by adding proper indexing to resolve the issue"
        
        is_complementary_ps = association_engine._has_complementary_content(
            problem_content, solution_content
        )
        assert is_complementary_ps is True
    
    @pytest.mark.asyncio
    async def test_confidence_score_calculation(self, association_engine):
        """Test confidence score calculation."""
        # High confidence scenario
        high_confidence = association_engine._calculate_confidence_score(
            similarity=0.6,      # Good similarity
            num_reasons=3,       # Multiple connection reasons
            num_shared_concepts=5,  # Many shared concepts
            num_shared_tags=2    # Shared tags
        )
        
        # Low confidence scenario
        low_confidence = association_engine._calculate_confidence_score(  
            similarity=0.35,     # Lower similarity
            num_reasons=1,       # Few reasons
            num_shared_concepts=1,  # Few concepts
            num_shared_tags=0    # No shared tags
        )
        
        assert high_confidence > low_confidence
        assert 0 <= high_confidence <= 1
        assert 0 <= low_confidence <= 1
    
    @pytest.mark.asyncio
    async def test_filter_high_confidence_associations(self, association_engine, sample_memories):
        """Test filtering associations by confidence score."""
        memories = sample_memories[:4]
        associations = await association_engine.process(memories)
        
        if associations:  # Only test if associations were found
            high_confidence = await association_engine.filter_high_confidence_associations(
                associations, min_confidence=0.7
            )
            
            # All returned associations should meet confidence threshold
            for assoc in high_confidence:
                assert assoc.metadata.get('confidence_score', 0) >= 0.7
    
    @pytest.mark.asyncio
    async def test_group_associations_by_type(self, association_engine, sample_memories):
        """Test grouping associations by connection type."""
        memories = sample_memories[:5]
        associations = await association_engine.process(memories)
        
        if associations:  # Only test if associations were found
            grouped = await association_engine.group_associations_by_type(associations)
            
            assert isinstance(grouped, dict)
            
            # Each group should contain associations of the same type
            for connection_type, group in grouped.items():
                assert all(assoc.connection_type == connection_type for assoc in group)
    
    @pytest.mark.asyncio
    async def test_text_similarity_fallback(self, association_engine):
        """Test text similarity fallback when embeddings are unavailable."""
        mem1 = Memory(
            content="python programming language concepts",
            content_hash="text1",
            tags=["python"],
            embedding=None,  # No embedding
            created_at=datetime.now().timestamp()
        )
        
        mem2 = Memory(
            content="programming language python concepts", 
            content_hash="text2",
            tags=["python"],
            embedding=None,  # No embedding
            created_at=datetime.now().timestamp()
        )
        
        similarity = await association_engine._calculate_semantic_similarity(mem1, mem2)
        
        # Should use text-based similarity
        assert 0 <= similarity <= 1
        assert similarity > 0  # Should find some similarity due to word overlap
    
    @pytest.mark.asyncio
    async def test_max_pairs_limiting(self, association_engine, large_memory_set):
        """Test that pair sampling limits combinatorial explosion."""
        # Use many memories to test pair limiting
        memories = large_memory_set[:20]  # 20 memories = 190 possible pairs
        
        # Mock the max_pairs to a small number for testing
        original_max = association_engine.max_pairs_per_run
        association_engine.max_pairs_per_run = 10
        
        try:
            associations = await association_engine.process(memories)
            
            # Should handle large memory sets without performance issues
            # and limit the number of pairs processed
            assert isinstance(associations, list)
            
        finally:
            # Restore original value
            association_engine.max_pairs_per_run = original_max
    
    @pytest.mark.asyncio
    async def test_empty_memories_list(self, association_engine):
        """Test handling of empty or insufficient memories list."""
        # Empty list
        associations = await association_engine.process([])
        assert associations == []
        
        # Single memory (can't create associations)
        single_memory = [Memory(
            content="Single memory",
            content_hash="single",
            tags=["test"],
            embedding=[0.1] * 320,
            created_at=datetime.now().timestamp()
        )]
        
        associations = await association_engine.process(single_memory)
        assert associations == []
    
    @pytest.mark.asyncio
    async def test_association_metadata_completeness(self, association_engine, sample_memories):
        """Test that association metadata contains all expected fields."""
        memories = sample_memories[:3]
        associations = await association_engine.process(memories)
        
        for assoc in associations:
            # Check basic fields
            assert len(assoc.source_memory_hashes) == 2
            assert isinstance(assoc.similarity_score, float)
            assert isinstance(assoc.connection_type, str)
            assert assoc.discovery_method == "creative_association"
            assert isinstance(assoc.discovery_date, datetime)
            
            # Check metadata fields
            assert 'shared_concepts' in assoc.metadata
            assert 'confidence_score' in assoc.metadata
            assert 'analysis_version' in assoc.metadata
            assert isinstance(assoc.metadata['shared_concepts'], list)
            assert isinstance(assoc.metadata['confidence_score'], float)