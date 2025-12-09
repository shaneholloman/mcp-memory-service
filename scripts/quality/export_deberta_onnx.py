#!/usr/bin/env python3
"""
Export NVIDIA DeBERTa quality classifier to ONNX format.

This script exports the NVIDIA quality-classifier-deberta model
from HuggingFace to ONNX format for local inference.

Usage:
    python scripts/quality/export_deberta_onnx.py

The exported model will be cached at:
    ~/.cache/mcp_memory/onnx_models/nvidia-quality-classifier-deberta/
"""

import sys
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp_memory_service.quality.onnx_ranker import get_onnx_ranker_model

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Export NVIDIA DeBERTa to ONNX format."""
    print("=" * 80)
    print("NVIDIA DeBERTa Quality Classifier - ONNX Export")
    print("=" * 80)
    print()

    logger.info("Initializing DeBERTa model (this will trigger ONNX export if needed)...")

    try:
        # Create model instance - will automatically export to ONNX if not present
        model = get_onnx_ranker_model(
            model_name='nvidia-quality-classifier-deberta',
            device='cpu'  # Use CPU for export (GPU-specific optimizations happen at runtime)
        )

        if model is None:
            logger.error("Failed to create DeBERTa model")
            logger.error("Check that you have transformers and torch installed:")
            logger.error("  pip install transformers torch onnx onnxruntime")
            return 1

        # Verify model works with a test inference
        logger.info("Testing model with sample input...")
        test_content = "This is a high-quality, comprehensive guide with detailed examples and best practices."
        test_score = model.score_quality("", test_content)  # Empty query for classifier

        logger.info(f"Test inference successful! Score: {test_score:.3f}")

        print()
        print("=" * 80)
        print("✅ SUCCESS!")
        print("=" * 80)
        print()
        print(f"Model cached at: {model.MODEL_PATH}")
        print(f"Model type: {model.model_config['type']}")
        print(f"Model size: {model.model_config['size_mb']}MB")
        print()
        print("The model is now ready for use.")
        print("It will automatically load from cache on subsequent uses.")
        print()
        print("Next steps:")
        print("  1. Update .env: export MCP_QUALITY_LOCAL_MODEL=nvidia-quality-classifier-deberta")
        print("  2. Restart MCP services")
        print("  3. Run bulk evaluation: python scripts/quality/bulk_evaluate_onnx.py")

        return 0

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        print()
        print("=" * 80)
        print("❌ EXPORT FAILED")
        print("=" * 80)
        print()
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Ensure dependencies are installed: pip install transformers torch onnx onnxruntime")
        print("  2. Check internet connection (model downloads from HuggingFace)")
        print("  3. Verify disk space (~500MB needed for model)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
