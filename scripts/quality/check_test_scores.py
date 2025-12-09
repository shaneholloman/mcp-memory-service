#!/usr/bin/env python3
"""Check actual scores for test cases to calibrate expectations."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service.quality.onnx_ranker import ONNXRankerModel

def main():
    print("Initializing DeBERTa model...")
    model = ONNXRankerModel(model_name="nvidia-quality-classifier-deberta", device="cpu")

    # Test cases from test_deberta_absolute_quality_scoring
    print("\n" + "="*80)
    print("TEST 1: test_deberta_absolute_quality_scoring")
    print("="*80)

    high_quality_1 = "Implement caching layer for API responses with Redis backend. Use TTL of 1 hour for user data."
    high_quality_2 = "Fix bug in user authentication flow. Added proper session validation and error handling."
    low_quality = "TODO: check this"

    score1 = model.score_quality("", high_quality_1)
    score2 = model.score_quality("", high_quality_2)
    score3 = model.score_quality("", low_quality)

    print(f"High quality 1: {score1:.4f} (expected ≥0.6)")
    print(f"High quality 2: {score2:.4f} (expected ≥0.6)")
    print(f"Low quality:    {score3:.4f} (expected <0.4)")

    # Test cases from test_deberta_3class_output_mapping
    print("\n" + "="*80)
    print("TEST 2: test_deberta_3class_output_mapping")
    print("="*80)

    excellent = "The implementation uses a sophisticated multi-tier architecture with semantic analysis, pattern matching, and adaptive learning algorithms to optimize retrieval accuracy."
    average = "The code does some processing and returns a result."
    poor = "stuff things maybe later TODO"

    score_excellent = model.score_quality("", excellent)
    score_average = model.score_quality("", average)
    score_poor = model.score_quality("", poor)

    print(f"Excellent: {score_excellent:.4f}")
    print(f"Average:   {score_average:.4f}")
    print(f"Poor:      {score_poor:.4f}")
    print(f"Range:     {max(score_excellent, score_average, score_poor) - min(score_excellent, score_average, score_poor):.4f} (expected >0.2)")
    print(f"Ordered correctly: {score_excellent > score_average > score_poor}")

    # Additional realistic test cases
    print("\n" + "="*80)
    print("ADDITIONAL TESTS: Realistic memory content")
    print("="*80)

    tests = [
        ("Configured CI/CD pipeline with GitHub Actions. Set up automated testing, linting, and deployment to production on merge to main branch. Added branch protection rules.", "DevOps implementation"),
        ("Refactored authentication module to use JWT tokens instead of session cookies. Implemented refresh token rotation and secure token storage in httpOnly cookies.", "Security improvement"),
        ("Updated README with installation instructions", "Documentation update"),
        ("Meeting notes: discussed project timeline", "Generic notes"),
        ("TODO", "Minimal content"),
        ("test", "Single word"),
    ]

    for content, label in tests:
        score = model.score_quality("", content)
        print(f"{score:.4f} - {label}")
        print(f"        Content: {content[:60]}...")

if __name__ == "__main__":
    main()
