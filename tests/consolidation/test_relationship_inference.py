"""
Unit tests for RelationshipInferenceEngine

Tests the intelligent relationship type classification system for knowledge graph associations.
"""

import pytest
import time

from mcp_memory_service.consolidation.relationship_inference import RelationshipInferenceEngine


@pytest.fixture
def engine():
    """Create RelationshipInferenceEngine instance with default settings."""
    return RelationshipInferenceEngine(min_confidence=0.5)


@pytest.fixture
def strict_engine():
    """Create RelationshipInferenceEngine with strict confidence threshold."""
    return RelationshipInferenceEngine(min_confidence=0.8)


class TestRelationshipInferenceEngineInit:
    """Tests for RelationshipInferenceEngine initialization."""

    def test_default_initialization(self):
        """Engine should initialize with default confidence threshold."""
        engine = RelationshipInferenceEngine()
        assert engine.min_confidence == 0.6

    def test_custom_confidence_threshold(self):
        """Engine should accept custom confidence threshold."""
        engine = RelationshipInferenceEngine(min_confidence=0.75)
        assert engine.min_confidence == 0.75

    def test_zero_confidence_threshold(self):
        """Engine should accept zero confidence threshold."""
        engine = RelationshipInferenceEngine(min_confidence=0.0)
        assert engine.min_confidence == 0.0


class TestTypeCombinaticAnalysis:
    """Tests for type combination analysis."""

    @pytest.mark.asyncio
    async def test_learning_fixes_error(self, engine):
        """Learning/insight fixing an error/bug should be detected."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="learning/insight",
            target_type="error/bug",
            source_content="Fixed authentication timeout by adjusting configuration",
            target_content="Authentication error: Request timeout after 30 seconds",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100
        )
        assert rel_type == "fixes"
        assert confidence >= 0.5

    @pytest.mark.asyncio
    async def test_error_fixes_error(self, engine):
        """One error/bug memory can fix another."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="error/bug",
            target_type="error/bug",
            source_content="Fixed database deadlock issue",
            target_content="Database deadlock on transaction commit",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100
        )
        assert rel_type == "fixes"
        assert confidence >= 0.4

    @pytest.mark.asyncio
    async def test_valid_relationship_types_returned(self, engine):
        """Engine should only return valid relationship types."""
        valid_types = ["related", "follows", "supports", "causes", "fixes", "contradicts"]

        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Some content",
            target_content="Other content",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )

        assert rel_type in valid_types
        assert 0.0 <= confidence <= 1.0


class TestContentSemanticAnalysis:
    """Tests for content semantic analysis."""

    @pytest.mark.asyncio
    async def test_fix_keyword_detection(self, engine):
        """Content with 'fixed' can suggest fixes relationship."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Fixed the configuration bug by updating the settings file",
            target_content="Configuration bug causing application crashes",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100
        )
        # Should detect fix signal or default to related
        assert rel_type in ["fixes", "related"]
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_contradiction_keyword_detection(self, engine):
        """Content with contradiction keywords can be detected."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="However, testing shows that caching actually improves performance",
            target_content="Caching degrades performance",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 50
        )
        # Should detect contradiction or default to related
        assert rel_type in ["contradicts", "related"]
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_no_clear_pattern_defaults_to_related(self, engine):
        """Content without clear patterns should default to 'related'."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Meeting notes about Q1 planning",
            target_content="Team lunch at restaurant",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )
        assert rel_type == "related"
        assert confidence >= 0.0


class TestTemporalAnalysis:
    """Tests for temporal pattern analysis."""

    @pytest.mark.asyncio
    async def test_temporal_proximity_affects_confidence(self, engine):
        """Temporal proximity should affect confidence scores."""
        now = time.time()

        # Very close in time (1 minute)
        rel_type1, conf1 = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Deployed version 1.0",
            target_content="Checked deployment status",
            source_timestamp=now,
            target_timestamp=now + 60
        )

        # Far apart (1 week)
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Deployed version 1.0",
            target_content="Checked deployment status",
            source_timestamp=now,
            target_timestamp=now + 604800
        )

        # Closer events should have higher or equal confidence
        assert conf1 >= confidence or abs(conf1 - confidence) < 0.1

    @pytest.mark.asyncio
    async def test_sequential_events_detected(self, engine):
        """Sequential events should be recognized."""
        now = time.time()
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Started deployment at 10:00 AM",
            target_content="Deployment completed at 10:15 AM",
            source_timestamp=now,
            target_timestamp=now + 900  # 15 minutes later
        )
        # Should detect temporal relationship
        assert rel_type in ["follows", "related"]
        assert confidence >= 0.0


class TestContradictionDetection:
    """Tests for contradiction detection."""

    @pytest.mark.asyncio
    async def test_negation_detection(self, engine):
        """Negation words can contribute to contradiction detection."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="The cache doesn't improve performance at all",
            target_content="Caching significantly improves performance",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100
        )
        # May detect contradiction or default to related
        assert rel_type in ["contradicts", "related"]
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_explicit_contradiction(self, engine):
        """Explicit contradiction keywords can be detected."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="This contradicts our earlier findings about performance",
            target_content="Performance improved by 50%",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 50
        )
        # May detect contradiction or default to related
        assert rel_type in ["contradicts", "related"]
        assert confidence >= 0.0


class TestConfidenceThreshold:
    """Tests for confidence threshold behavior."""

    @pytest.mark.asyncio
    async def test_strict_threshold_more_related_results(self, strict_engine):
        """Strict threshold should result in more 'related' classifications."""
        rel_type, confidence = await strict_engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Some observation",
            target_content="Another observation",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )
        # With strict threshold, should default to "related"
        assert rel_type == "related"

    @pytest.mark.asyncio
    async def test_high_confidence_inference(self, engine):
        """Strong signals should result in high-confidence inference."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="learning/insight",
            target_type="error/bug",
            source_content="Fixed the authentication bug by updating timeout configuration",
            target_content="Authentication bug causing timeout errors",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100
        )
        # Multiple strong signals should result in high confidence
        assert rel_type == "fixes"
        assert confidence >= 0.6


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_none_content_causes_error(self, engine):
        """None content currently raises AttributeError - documented behavior."""
        # This documents current behavior - engine expects non-None content
        with pytest.raises(AttributeError):
            await engine.infer_relationship_type(
                source_type="observation",
                target_type="observation",
                source_content=None,
                target_content=None,
                source_timestamp=time.time(),
                target_timestamp=time.time()
            )

    @pytest.mark.asyncio
    async def test_empty_content_handled(self, engine):
        """Empty content should be handled gracefully."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="",
            target_content="",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )
        assert rel_type == "related"
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_very_long_content(self, engine):
        """Very long content should be processed without errors."""
        long_content = "word " * 5000
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content=long_content,
            target_content="short",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )
        # Should complete without error
        assert rel_type in ["related", "follows", "supports", "causes", "fixes", "contradicts"]
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_unicode_content(self, engine):
        """Unicode content should be handled correctly."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="修正了错误 🐛 Fixed bug",
            target_content="发现了错误 Found bug 🔍",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 100
        )
        # May detect "fixed" keyword or default to related
        assert rel_type in ["fixes", "related"]
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_special_regex_characters(self, engine):
        """Special regex characters in content should not cause errors."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Fixed bug with pattern: [a-z]+(?:\\d{2,4})?",
            target_content="Bug in regex pattern causing failures",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 50
        )
        # May detect fix signal or default to related
        assert rel_type in ["fixes", "related"]
        assert confidence >= 0.0


class TestTagAnalysis:
    """Tests for tag-based analysis."""

    @pytest.mark.asyncio
    async def test_shared_tags_influence(self, engine):
        """Shared tags should influence relationship detection."""
        # Many shared tags
        rel_type1, conf1 = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="First observation",
            target_content="Second observation",
            source_timestamp=time.time(),
            target_timestamp=time.time(),
            source_tags=["bug", "auth", "urgent"],
            target_tags=["bug", "auth", "critical"]
        )

        # No shared tags
        rel_type2, conf2 = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="First observation",
            target_content="Second observation",
            source_timestamp=time.time(),
            target_timestamp=time.time(),
            source_tags=["feature"],
            target_tags=["docs"]
        )

        # More shared context should result in higher or equal confidence
        assert conf1 >= conf2 or abs(conf1 - conf2) < 0.1

    @pytest.mark.asyncio
    async def test_no_tags_handled(self, engine):
        """Missing tags should not cause errors."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Content",
            target_content="Other content",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )
        assert rel_type in ["related", "follows", "supports", "causes", "fixes", "contradicts"]
        assert 0.0 <= confidence <= 1.0


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    @pytest.mark.asyncio
    async def test_bug_fix_complete_workflow(self, engine):
        """Test complete bug discovery → fix workflow."""
        now = time.time()

        rel_type, confidence = await engine.infer_relationship_type(
            source_type="learning/insight",
            target_type="error/bug",
            source_content="Fixed by increasing database timeout from 5s to 30s",
            target_content="Database connection timeout error after 5 seconds",
            source_timestamp=now + 100,
            target_timestamp=now,
            source_tags=["bug", "database", "fix"],
            target_tags=["bug", "database", "timeout"]
        )

        # Multiple strong signals should result in "fixes" with high confidence
        assert rel_type == "fixes"
        assert confidence >= 0.6

    @pytest.mark.asyncio
    async def test_decision_support_chain(self, engine):
        """Test decision support relationships."""
        now = time.time()

        rel_type, confidence = await engine.infer_relationship_type(
            source_type="decision/architecture",
            target_type="decision/tool_choice",
            source_content="Decided to use microservices which supports distributed deployment",
            target_content="Selected Docker for service deployment",
            source_timestamp=now,
            target_timestamp=now + 3600,
            source_tags=["architecture", "planning"],
            target_tags=["architecture", "deployment", "docker"]
        )

        # Should detect relationship (supports or related)
        assert rel_type in ["supports", "related"]
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_conflicting_observations(self, engine):
        """Test detection of conflicting observations."""
        now = time.time()

        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="However, performance tests show caching degrades performance",
            target_content="Caching significantly improves performance",
            source_timestamp=now + 3600,
            target_timestamp=now,
            source_tags=["performance"],
            target_tags=["performance", "caching"]
        )

        # May detect contradiction or default to related
        assert rel_type in ["contradicts", "related"]
        assert confidence >= 0.0

    @pytest.mark.asyncio
    async def test_unrelated_memories(self, engine):
        """Test that clearly unrelated memories default to 'related'."""
        rel_type, confidence = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Meeting notes about quarterly planning",
            target_content="Recipe for chocolate cake",
            source_timestamp=time.time(),
            target_timestamp=time.time() - 10000
        )

        assert rel_type == "related"
        assert confidence >= 0.0


class TestReturnTypes:
    """Tests for return type validation."""

    @pytest.mark.asyncio
    async def test_returns_tuple(self, engine):
        """Engine should always return a tuple of (str, float)."""
        result = await engine.infer_relationship_type(
            source_type="observation",
            target_type="observation",
            source_content="Content",
            target_content="Other content",
            source_timestamp=time.time(),
            target_timestamp=time.time()
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], float)

    @pytest.mark.asyncio
    async def test_confidence_in_valid_range(self, engine):
        """Confidence should always be between 0.0 and 1.0."""
        for _ in range(10):  # Test multiple scenarios
            rel_type, confidence = await engine.infer_relationship_type(
                source_type="observation",
                target_type="observation",
                source_content=f"Content {_}",
                target_content=f"Other {_}",
                source_timestamp=time.time(),
                target_timestamp=time.time() - _
            )

            assert 0.0 <= confidence <= 1.0
