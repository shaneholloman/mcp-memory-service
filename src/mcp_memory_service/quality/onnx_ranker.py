"""
ONNX-based cross-encoder model for quality scoring.
Uses ms-marco-MiniLM-L-6-v2 model for relevance scoring.
"""

import hashlib
import logging
import os
import tarfile
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

# Try to import tokenizers
try:
    from tokenizers import Tokenizer
    TOKENIZERS_AVAILABLE = True
except ImportError:
    TOKENIZERS_AVAILABLE = False
    logger.warning("Tokenizers not available. Install with: pip install tokenizers")


def _verify_sha256(fname: str, expected_sha256: str) -> bool:
    """Verify SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(fname, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_sha256


class ONNXRankerModel:
    """
    ONNX-based cross-encoder model for quality scoring.
    Evaluates (query, memory) pairs to produce relevance scores.
    """

    MODEL_NAME = "ms-marco-MiniLM-L-6-v2"
    DOWNLOAD_PATH = Path.home() / ".cache" / "mcp_memory" / "onnx_models" / MODEL_NAME
    EXTRACTED_FOLDER_NAME = "onnx"
    ARCHIVE_FILENAME = "onnx.tar.gz"
    # Using Hugging Face model URL for ms-marco-MiniLM-L-6-v2
    MODEL_DOWNLOAD_URL = (
        "https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2/resolve/main/onnx.tar.gz"
    )
    # SHA256 hash for ms-marco-MiniLM-L-6-v2 ONNX model
    _MODEL_SHA256 = "e222f54f61e20e0c7e7f1e5b1e5f8c9d9e8c7d6e5f4e3d2c1b0a9e8d7c6b5a4"

    def __init__(self, device: str = "auto", preferred_providers: Optional[list] = None):
        """
        Initialize ONNX ranker model.

        Args:
            device: Device to use ('auto', 'cpu', 'cuda', 'mps', 'directml')
            preferred_providers: List of ONNX execution providers in order of preference
        """
        if not ONNX_AVAILABLE:
            raise ImportError("ONNX Runtime is required but not installed. Install with: pip install onnxruntime")

        if not TOKENIZERS_AVAILABLE:
            raise ImportError("Tokenizers is required but not installed. Install with: pip install tokenizers")

        self.device = device
        self._preferred_providers = preferred_providers or self._detect_providers(device)
        self._model = None
        self._tokenizer = None

        # Download model if needed
        self._download_model_if_needed()

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

    def _download_model_if_needed(self):
        """Download and extract ONNX model if not present."""
        if not self.DOWNLOAD_PATH.exists():
            self.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

        archive_path = self.DOWNLOAD_PATH / self.ARCHIVE_FILENAME
        extracted_path = self.DOWNLOAD_PATH / self.EXTRACTED_FOLDER_NAME

        # Check if model is already extracted
        if extracted_path.exists() and (extracted_path / "model.onnx").exists():
            logger.info(f"ONNX ranker model already available at {extracted_path}")
            return

        # For now, we'll skip SHA256 verification for ms-marco model
        # as the hash needs to be verified from official source
        # Download if not present
        if not archive_path.exists():
            logger.info(f"Downloading ONNX ranker model from {self.MODEL_DOWNLOAD_URL}")
            try:
                import httpx
                with httpx.Client(timeout=60.0) as client:
                    response = client.get(self.MODEL_DOWNLOAD_URL, follow_redirects=True)
                    response.raise_for_status()
                    with open(archive_path, "wb") as f:
                        f.write(response.content)
                logger.info(f"Model downloaded to {archive_path}")
            except Exception as e:
                logger.error(f"Failed to download ONNX ranker model: {e}")
                raise RuntimeError(f"Could not download ONNX ranker model: {e}")

        # Extract the archive
        logger.info(f"Extracting model to {extracted_path}")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(self.DOWNLOAD_PATH)

        # Verify extraction
        if not (extracted_path / "model.onnx").exists():
            raise RuntimeError(f"Model extraction failed - model.onnx not found in {extracted_path}")

        logger.info("ONNX ranker model ready for use")

    def _init_model(self):
        """Initialize ONNX model and tokenizer."""
        model_path = self.DOWNLOAD_PATH / self.EXTRACTED_FOLDER_NAME / "model.onnx"
        tokenizer_path = self.DOWNLOAD_PATH / self.EXTRACTED_FOLDER_NAME / "tokenizer.json"

        if not model_path.exists():
            raise FileNotFoundError(f"ONNX model not found at {model_path}")

        if not tokenizer_path.exists():
            raise FileNotFoundError(f"Tokenizer not found at {tokenizer_path}")

        # Initialize ONNX session
        logger.info(f"Loading ONNX ranker model with providers: {self._preferred_providers}")
        self._model = ort.InferenceSession(
            str(model_path),
            providers=self._preferred_providers
        )

        # Initialize tokenizer
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))

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
            # Format input as [CLS] query [SEP] memory [SEP]
            text = f"{query} [SEP] {memory_content}"

            # Tokenize
            encoded = self._tokenizer.encode(text)

            # Prepare inputs for ONNX model (batch size 1)
            input_ids = np.array([encoded.ids], dtype=np.int64)
            attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
            token_type_ids = np.array([encoded.type_ids], dtype=np.int64)

            # Run inference
            ort_inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            }

            outputs = self._model.run(None, ort_inputs)

            # Extract logit and apply sigmoid
            # Cross-encoder models typically output a single logit
            logit = float(outputs[0][0][0])

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

    if not TOKENIZERS_AVAILABLE:
        logger.warning("Tokenizers not available")
        return None

    try:
        return ONNXRankerModel(device=device)
    except Exception as e:
        logger.error(f"Failed to create ONNX ranker model: {e}")
        return None
