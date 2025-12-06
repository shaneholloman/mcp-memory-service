"""
ONNX-based cross-encoder model for quality scoring.
Uses ms-marco-MiniLM-L-6-v2 model for relevance scoring.

Exports the model from transformers to ONNX format on first use.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

# Try to import ONNX Runtime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime not available. Install with: pip install onnxruntime")

# Try to import transformers for model export
try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available. Install with: pip install transformers torch")


class ONNXRankerModel:
    """
    ONNX-based cross-encoder model for quality scoring.
    Evaluates (query, memory) pairs to produce relevance scores.

    On first use, exports the model from transformers to ONNX format.
    """

    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    MODEL_PATH = Path.home() / ".cache" / "mcp_memory" / "onnx_models" / "ms-marco-MiniLM-L-6-v2"
    ONNX_MODEL_FILE = "model.onnx"

    def __init__(self, device: str = "auto", preferred_providers: Optional[list] = None):
        """
        Initialize ONNX ranker model.

        Args:
            device: Device to use ('auto', 'cpu', 'cuda', 'mps', 'directml')
            preferred_providers: List of ONNX execution providers in order of preference
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX Runtime is required but not installed. Install with: pip install onnxruntime")

        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers and torch are required. Install with: pip install transformers torch")

        self.device = device
        self._preferred_providers = preferred_providers or self._detect_providers(device)
        self._model = None
        self._tokenizer = None

        # Ensure model is exported to ONNX
        self._ensure_onnx_model()

        # Initialize the model
        self._init_model()

    def _detect_providers(self, device: str) -> list:
        """Detect best available ONNX execution providers based on device preference."""
        available_providers = ort.get_available_providers()
        preferred_providers = []

        if device == "auto":
            # Prefer GPU providers if available
            if 'CUDAExecutionProvider' in available_providers:
                preferred_providers.append('CUDAExecutionProvider')
            if 'DirectMLExecutionProvider' in available_providers:
                preferred_providers.append('DirectMLExecutionProvider')
            if 'CoreMLExecutionProvider' in available_providers:
                preferred_providers.append('CoreMLExecutionProvider')
        elif device == "cuda" and 'CUDAExecutionProvider' in available_providers:
            preferred_providers.append('CUDAExecutionProvider')
        elif device == "mps" and 'CoreMLExecutionProvider' in available_providers:
            preferred_providers.append('CoreMLExecutionProvider')
        elif device == "directml" and 'DirectMLExecutionProvider' in available_providers:
            preferred_providers.append('DirectMLExecutionProvider')

        # Always include CPU as fallback
        preferred_providers.append('CPUExecutionProvider')

        return preferred_providers

    def _ensure_onnx_model(self):
        """Export transformers model to ONNX format if not already present."""
        onnx_path = self.MODEL_PATH / self.ONNX_MODEL_FILE

        if onnx_path.exists():
            logger.info(f"ONNX model already available at {onnx_path}")
            return

        # Create directory
        self.MODEL_PATH.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting {self.MODEL_NAME} to ONNX format...")

        # Load transformers model (try local_files_only first for offline mode)
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME, local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME, local_files_only=True)
        except Exception:
            # Fall back to online mode if not cached
            logger.info("Model not in cache, downloading...")
            tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)

        model.eval()

        # Create dummy inputs for export
        dummy_text = "query [SEP] document"
        inputs = tokenizer(dummy_text, return_tensors="pt", padding=True, truncation=True)

        # Export to ONNX
        with torch.no_grad():
            torch.onnx.export(
                model,
                (inputs["input_ids"], inputs["attention_mask"], inputs["token_type_ids"]),
                str(onnx_path),
                input_names=["input_ids", "attention_mask", "token_type_ids"],
                output_names=["logits"],
                dynamic_axes={
                    "input_ids": {0: "batch", 1: "sequence"},
                    "attention_mask": {0: "batch", 1: "sequence"},
                    "token_type_ids": {0: "batch", 1: "sequence"},
                    "logits": {0: "batch"},
                },
                opset_version=14,
            )

        # Save tokenizer config for loading
        tokenizer.save_pretrained(str(self.MODEL_PATH))

        logger.info(f"ONNX model exported to {onnx_path}")

    def _init_model(self):
        """Initialize ONNX model and tokenizer."""
        onnx_path = self.MODEL_PATH / self.ONNX_MODEL_FILE

        if not onnx_path.exists():
            raise FileNotFoundError(f"ONNX model not found at {onnx_path}")

        # Initialize ONNX session
        logger.info(f"Loading ONNX ranker model with providers: {self._preferred_providers}")
        self._model = ort.InferenceSession(
            str(onnx_path),
            providers=self._preferred_providers
        )

        # Initialize tokenizer from saved pretrained files (local only)
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.MODEL_PATH), local_files_only=True)

        logger.info(f"ONNX ranker model loaded. Active provider: {self._model.get_providers()[0]}")

    def score_quality(self, query: str, memory_content: str) -> float:
        """
        Score the quality/relevance of a memory for a given query.

        Args:
            query: The search query
            memory_content: The memory content to score

        Returns:
            Quality score between 0.0 and 1.0
        """
        if not query or not memory_content:
            return 0.0

        try:
            # Tokenize query-document pair
            inputs = self._tokenizer(
                query,
                memory_content,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="np"
            )

            # Prepare inputs for ONNX model
            ort_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64),
                "token_type_ids": inputs["token_type_ids"].astype(np.int64),
            }

            outputs = self._model.run(None, ort_inputs)

            # Extract logit and apply sigmoid
            # Cross-encoder models output logits for classification
            logits = outputs[0][0]
            # For binary classification, take first logit or single value
            logit = float(logits[0] if len(logits.shape) > 0 and logits.shape[0] > 1 else logits)

            # Apply sigmoid to convert to 0-1 range
            score = 1.0 / (1.0 + np.exp(-logit))

            return score

        except Exception as e:
            logger.error(f"Error scoring quality: {e}")
            return 0.5  # Return neutral score on error


def get_onnx_ranker_model(device: str = "auto") -> Optional[ONNXRankerModel]:
    """
    Get ONNX ranker model if available.

    Args:
        device: Device to use ('auto', 'cpu', 'cuda', 'mps', 'directml')

    Returns:
        ONNXRankerModel instance or None if ONNX is not available
    """
    if not ONNX_AVAILABLE:
        logger.warning("ONNX Runtime not available")
        return None

    if not TRANSFORMERS_AVAILABLE:
        logger.warning("Transformers not available")
        return None

    try:
        return ONNXRankerModel(device=device)
    except Exception as e:
        logger.error(f"Failed to create ONNX ranker model: {e}")
        return None
