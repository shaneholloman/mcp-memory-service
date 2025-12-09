"""Tests for NVIDIA DeBERTa quality classifier integration."""

import pytest
from pathlib import Path
from mcp_memory_service.quality.onnx_ranker import ONNXRankerModel, get_onnx_ranker_model
from mcp_memory_service.quality.config import QualityConfig, SUPPORTED_MODELS

# Check if ONNX models are available
DEBERTA_AVAILABLE = Path.home().joinpath(
    ".cache/mcp_memory/onnx_models/nvidia-quality-classifier-deberta/model.onnx"
).exists()
MS_MARCO_AVAILABLE = Path.home().joinpath(
    ".cache/mcp_memory/onnx_models/ms-marco-MiniLM-L-6-v2/model.onnx"
).exists()


class TestModelRegistry:
    """Test model registry configuration."""

    def test_supported_models_exist(self):
        """Verify SUPPORTED_MODELS contains both models."""
        assert 'nvidia-quality-classifier-deberta' in SUPPORTED_MODELS
        assert 'ms-marco-MiniLM-L-6-v2' in SUPPORTED_MODELS

    def test_deberta_config_structure(self):
        """Verify DeBERTa model configuration."""
        config = SUPPORTED_MODELS['nvidia-quality-classifier-deberta']
        assert config['hf_name'] == 'nvidia/quality-classifier-deberta'
        assert config['type'] == 'classifier'
        assert config['size_mb'] == 450
        assert 'input_ids' in config['inputs']
        assert 'attention_mask' in config['inputs']
        assert 'token_type_ids' not in config['inputs']  # Key difference from MS-MARCO
        assert config['output_classes'] == ['low', 'medium', 'high']

    def test_ms_marco_config_structure(self):
        """Verify MS-MARCO model configuration."""
        config = SUPPORTED_MODELS['ms-marco-MiniLM-L-6-v2']
        assert config['hf_name'] == 'cross-encoder/ms-marco-MiniLM-L-6-v2'
        assert config['type'] == 'cross-encoder'
        assert config['size_mb'] == 23
        assert 'input_ids' in config['inputs']
        assert 'attention_mask' in config['inputs']
        assert 'token_type_ids' in config['inputs']  # Required for cross-encoder
        assert config['output_classes'] is None  # Continuous score

    def test_config_default_is_deberta(self):
        """Verify DeBERTa is the default model."""
        config = QualityConfig()
        assert config.local_model == 'nvidia-quality-classifier-deberta'


@pytest.mark.skipif(not DEBERTA_AVAILABLE, reason="DeBERTa ONNX model not exported")
class TestDeBERTaIntegration:
    """Test NVIDIA DeBERTa quality classifier."""

    def test_deberta_initialization(self):
        """Test DeBERTa model initialization."""
        model = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'
        )
        assert model is not None
        assert model.model_name == 'nvidia-quality-classifier-deberta'
        assert model.model_config['type'] == 'classifier'

    def test_deberta_absolute_quality_scoring(self):
        """Test DeBERTa scores absolute quality (query-independent)."""
        model = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'
        )

        # High-quality memory content
        high_quality = (
            "This implementation uses async/await patterns with proper error handling, "
            "comprehensive logging, and follows Python best practices. The code includes "
            "detailed docstrings, type hints, and handles edge cases gracefully. "
            "Performance is optimized with caching and batch processing."
        )

        # Low-quality memory content
        low_quality = "todo fix this later maybe idk lol"

        # Medium-quality memory content
        medium_quality = "Basic implementation that works but lacks documentation and error handling."

        # Query should not matter for classifier - test with different queries
        query_meaningful = "Python best practices"
        query_random = "xyzabc random words 12345"
        query_empty = ""

        # Score high-quality content with different queries
        high_score_1 = model.score_quality(query_meaningful, high_quality)
        high_score_2 = model.score_quality(query_random, high_quality)
        high_score_3 = model.score_quality(query_empty, high_quality)

        # Score low-quality content with different queries
        low_score_1 = model.score_quality(query_meaningful, low_quality)
        low_score_2 = model.score_quality(query_random, low_quality)
        low_score_3 = model.score_quality(query_empty, low_quality)

        # Score medium-quality content
        medium_score = model.score_quality(query_empty, medium_quality)

        # High-quality content should score high (≥0.5)
        # Note: DeBERTa is more conservative than MS-MARCO, rarely giving scores >0.7
        assert high_score_1 >= 0.5, f"Expected high score ≥0.5, got {high_score_1}"
        assert high_score_2 >= 0.5, f"Expected high score ≥0.5, got {high_score_2}"
        assert high_score_3 >= 0.5, f"Expected high score ≥0.5, got {high_score_3}"

        # Low-quality content should score low (<0.4)
        assert low_score_1 < 0.4, f"Expected low score <0.4, got {low_score_1}"
        assert low_score_2 < 0.4, f"Expected low score <0.4, got {low_score_2}"
        assert low_score_3 < 0.4, f"Expected low score <0.4, got {low_score_3}"

        # Medium-quality content should be in middle range
        assert 0.4 <= medium_score <= 0.7, f"Expected medium score 0.4-0.7, got {medium_score}"

        # Scores should be similar regardless of query (±0.1 tolerance)
        # This validates query-independent behavior
        assert abs(high_score_1 - high_score_2) < 0.1, "High quality scores vary too much with query"
        assert abs(high_score_1 - high_score_3) < 0.1, "High quality scores vary too much with query"
        assert abs(low_score_1 - low_score_2) < 0.1, "Low quality scores vary too much with query"
        assert abs(low_score_1 - low_score_3) < 0.1, "Low quality scores vary too much with query"

        # Quality ranking should be consistent
        assert high_score_1 > medium_score > low_score_1, "Quality ranking incorrect"

    def test_deberta_3class_output_mapping(self):
        """Test 3-class output mapping to 0-1 scale."""
        model = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'
        )

        # Test various quality levels with concrete, specific content
        # (DeBERTa performs better on specific technical content vs abstract descriptions)
        excellent = (
            "The implementation uses a sophisticated multi-tier architecture with semantic analysis, "
            "pattern matching, and adaptive learning algorithms to optimize retrieval accuracy."
        )
        average = "The code does some processing and returns a result."
        poor = "stuff things maybe later TODO"

        scores = [
            model.score_quality("", excellent),
            model.score_quality("", average),
            model.score_quality("", poor)
        ]

        # Verify ordering (excellent > average > poor)
        assert scores[0] > scores[1] > scores[2], f"Scores not ordered correctly: {scores}"

        # Verify all scores in valid range [0.0, 1.0]
        assert all(0.0 <= s <= 1.0 for s in scores), f"Scores out of range: {scores}"

        # Verify reasonable spread (not all clustered near 0.5)
        score_range = max(scores) - min(scores)
        assert score_range > 0.2, f"Scores too clustered (range: {score_range})"

    def test_deberta_empty_content_handling(self):
        """Test DeBERTa handles empty content gracefully."""
        model = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'
        )

        # Empty content should return 0.0
        assert model.score_quality("", "") == 0.0
        assert model.score_quality("query", "") == 0.0


@pytest.mark.skipif(not MS_MARCO_AVAILABLE, reason="MS-MARCO ONNX model not found")
class TestBackwardCompatibility:
    """Test backward compatibility with MS-MARCO model."""

    def test_ms_marco_still_works(self):
        """Verify MS-MARCO model still initializes and works."""
        model = get_onnx_ranker_model(
            model_name='ms-marco-MiniLM-L-6-v2',
            device='cpu'
        )
        assert model is not None
        assert model.model_name == 'ms-marco-MiniLM-L-6-v2'
        assert model.model_config['type'] == 'cross-encoder'

    def test_ms_marco_relevance_scoring(self):
        """Test MS-MARCO scores query-document relevance."""
        model = get_onnx_ranker_model(
            model_name='ms-marco-MiniLM-L-6-v2',
            device='cpu'
        )

        content = "Python async/await patterns for concurrent programming."

        # Relevant query should score higher
        relevant_query = "Python asynchronous programming"
        irrelevant_query = "Java database optimization"

        relevant_score = model.score_quality(relevant_query, content)
        irrelevant_score = model.score_quality(irrelevant_query, content)

        # MS-MARCO should give higher score to relevant query
        assert relevant_score > irrelevant_score, (
            f"MS-MARCO should score relevant query higher: "
            f"relevant={relevant_score}, irrelevant={irrelevant_score}"
        )

        # Both scores should be valid
        assert 0.0 <= relevant_score <= 1.0
        assert 0.0 <= irrelevant_score <= 1.0

    def test_ms_marco_requires_query(self):
        """Test MS-MARCO requires non-empty query."""
        model = get_onnx_ranker_model(
            model_name='ms-marco-MiniLM-L-6-v2',
            device='cpu'
        )

        content = "Test content"

        # Empty query should return 0.0 for cross-encoder
        assert model.score_quality("", content) == 0.0

        # Non-empty query should work
        score = model.score_quality("test query", content)
        assert 0.0 < score <= 1.0

    def test_config_override_to_ms_marco(self):
        """Test users can override config back to MS-MARCO."""
        import os
        original_value = os.getenv('MCP_QUALITY_LOCAL_MODEL')

        try:
            os.environ['MCP_QUALITY_LOCAL_MODEL'] = 'ms-marco-MiniLM-L-6-v2'
            config = QualityConfig.from_env()
            assert config.local_model == 'ms-marco-MiniLM-L-6-v2'
        finally:
            # Restore original value
            if original_value:
                os.environ['MCP_QUALITY_LOCAL_MODEL'] = original_value
            else:
                os.environ.pop('MCP_QUALITY_LOCAL_MODEL', None)


@pytest.mark.benchmark
@pytest.mark.skipif(not DEBERTA_AVAILABLE, reason="DeBERTa ONNX model not exported")
class TestPerformance:
    """Performance benchmarks for DeBERTa."""

    def test_deberta_inference_speed(self):
        """Test DeBERTa inference completes within acceptable time."""
        import time

        model = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'
        )

        content = "Sample memory content for benchmarking quality scoring performance."

        # Warm-up inference
        model.score_quality("", content)

        # Benchmark 10 inferences
        start_time = time.time()
        for _ in range(10):
            score = model.score_quality("", content)
            assert 0.0 <= score <= 1.0

        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        avg_time_per_inference = elapsed_time / 10

        # Target: <200ms on CPU (DeBERTa is larger than MS-MARCO)
        assert avg_time_per_inference < 200, (
            f"DeBERTa inference too slow: {avg_time_per_inference:.1f}ms "
            f"(target: <200ms on CPU)"
        )

        print(f"\nDeBERTa performance: {avg_time_per_inference:.1f}ms per inference")

    @pytest.mark.skipif(not MS_MARCO_AVAILABLE, reason="MS-MARCO model not found")
    def test_performance_comparison(self):
        """Compare DeBERTa vs MS-MARCO inference speed."""
        import time

        deberta = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'
        )
        ms_marco = get_onnx_ranker_model(
            model_name='ms-marco-MiniLM-L-6-v2',
            device='cpu'
        )

        content = "Test content for performance comparison."
        query = "test query"

        # Warm-up
        deberta.score_quality("", content)
        ms_marco.score_quality(query, content)

        # Benchmark DeBERTa
        start = time.time()
        for _ in range(10):
            deberta.score_quality("", content)
        deberta_time = (time.time() - start) * 1000 / 10

        # Benchmark MS-MARCO
        start = time.time()
        for _ in range(10):
            ms_marco.score_quality(query, content)
        ms_marco_time = (time.time() - start) * 1000 / 10

        print(f"\nPerformance comparison:")
        print(f"  DeBERTa:  {deberta_time:.1f}ms per inference")
        print(f"  MS-MARCO: {ms_marco_time:.1f}ms per inference")
        print(f"  Overhead: {((deberta_time / ms_marco_time - 1) * 100):.1f}%")

        # DeBERTa should be slower (larger model: 450MB vs 23MB)
        # Target: <10x slower than MS-MARCO (typically 6-7x on CPU, 2-3x on GPU)
        # Note: Trade-off for better quality assessment and no self-matching bias
        assert deberta_time < ms_marco_time * 10, (
            f"DeBERTa excessively slow compared to MS-MARCO: "
            f"{deberta_time:.1f}ms vs {ms_marco_time:.1f}ms"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
