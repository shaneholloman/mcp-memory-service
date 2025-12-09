#!/usr/bin/env python3
"""
Debug script to examine DeBERTa raw outputs and scoring behavior.
"""
import sys
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service.quality.onnx_ranker import ONNXRankerModel

def analyze_scoring(model, text, label):
    """Analyze raw model outputs for debugging."""
    print(f"\n{'='*80}")
    print(f"Testing: {label}")
    print(f"Text: {text[:100]}...")
    print(f"{'='*80}")

    # Get inputs
    text_input = text[:512]
    inputs = model._tokenizer(
        text_input,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="np"
    )

    ort_inputs = {
        "input_ids": inputs["input_ids"].astype(np.int64),
        "attention_mask": inputs["attention_mask"].astype(np.int64)
    }

    # Run inference
    outputs = model._model.run(None, ort_inputs)
    logits = outputs[0][0]

    print(f"\nRaw logits: {logits}")
    print(f"Logits shape: {logits.shape}")

    # Apply softmax
    exp_logits = np.exp(logits - np.max(logits))
    probs = exp_logits / exp_logits.sum()

    print(f"\nSoftmax probabilities:")
    print(f"  P(Low):    {probs[0]:.6f}")
    print(f"  P(Medium): {probs[1]:.6f}")
    print(f"  P(High):   {probs[2]:.6f}")

    # Calculate score
    class_values = np.array([0.0, 0.5, 1.0])
    score = float(np.dot(probs, class_values))

    print(f"\nWeighted score: {score:.6f}")
    print(f"  Formula: 0.0×{probs[0]:.4f} + 0.5×{probs[1]:.4f} + 1.0×{probs[2]:.4f}")

    # Also get score via API
    api_score = model.score_quality("", text)
    print(f"  API score: {api_score:.6f}")

    return score, probs

def main():
    print("Initializing NVIDIA DeBERTa model...")
    model = ONNXRankerModel(model_name="nvidia-quality-classifier-deberta", device="cpu")

    # Test cases from the unit tests
    test_cases = [
        (
            "Implement caching layer for API responses with Redis backend. Use TTL of 1 hour for user data.",
            "High quality - specific implementation"
        ),
        (
            "Fix bug in user authentication flow. Added proper session validation and error handling.",
            "High quality - bug fix with details"
        ),
        (
            "Meeting notes from team sync. Discussed project timeline and resource allocation.",
            "Medium quality - general notes"
        ),
        (
            "Random thoughts about maybe doing something later.",
            "Low quality - vague"
        ),
        (
            "TODO: check this",
            "Low quality - minimal content"
        ),
        (
            "The implementation uses a sophisticated multi-tier architecture with semantic analysis, "
            "pattern matching, and adaptive learning algorithms to optimize retrieval accuracy.",
            "Excellent - from test"
        ),
        (
            "The code does some processing and returns a result.",
            "Average - from test"
        ),
        (
            "stuff things maybe later TODO",
            "Poor - from test"
        )
    ]

    results = []
    for text, label in test_cases:
        score, probs = analyze_scoring(model, text, label)
        results.append((label, score, probs))

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    for label, score, probs in results:
        print(f"{label:40s} | Score: {score:.4f} | P(H/M/L): {probs[2]:.3f}/{probs[1]:.3f}/{probs[0]:.3f}")

if __name__ == "__main__":
    main()
