"""
AI-powered quality evaluator with multi-tier fallback.
Coordinates between local SLM, Groq, Gemini, and implicit signals.
"""

import logging
from typing import Optional
from .config import QualityConfig
from .onnx_ranker import get_onnx_ranker_model, ONNXRankerModel
from .implicit_signals import ImplicitSignalsEvaluator
from ..models.memory import Memory

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """
    Multi-tier AI quality evaluator with fallback chain.
    Tries: Local ONNX → Groq → Gemini → Implicit Signals
    """

    def __init__(self, config: Optional[QualityConfig] = None):
        """
        Initialize quality evaluator with configuration.

        Args:
            config: Quality configuration (defaults to env-based config)
        """
        self.config = config or QualityConfig.from_env()
        self.config.validate()

        # Initialize tier components
        self._onnx_ranker: Optional[ONNXRankerModel] = None
        self._implicit_evaluator = ImplicitSignalsEvaluator()
        self._groq_bridge = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of heavy components."""
        if self._initialized:
            return

        # Initialize local ONNX ranker if using local provider
        if self.config.ai_provider in ['local', 'auto']:
            try:
                self._onnx_ranker = get_onnx_ranker_model(device=self.config.local_device)
                if self._onnx_ranker:
                    logger.info("ONNX ranker model initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize ONNX ranker: {e}")
                self._onnx_ranker = None

        # Initialize Groq bridge if using Groq provider
        if self.config.can_use_groq:
            try:
                # Import Groq bridge dynamically to avoid hard dependency
                import sys
                from pathlib import Path
                # Add scripts directory to path for import
                scripts_path = Path(__file__).parent.parent.parent.parent / 'scripts' / 'utils'
                if scripts_path.exists():
                    sys.path.insert(0, str(scripts_path))
                    from groq_agent_bridge import GroqAgentBridge
                    self._groq_bridge = GroqAgentBridge(api_key=self.config.groq_api_key)
                    logger.info("Groq bridge initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq bridge: {e}")
                self._groq_bridge = None

        self._initialized = True

    async def evaluate_quality(self, query: str, memory: Memory) -> float:
        """
        Evaluate memory quality using multi-tier approach.

        Args:
            query: Search query for context
            memory: Memory object to evaluate

        Returns:
            Quality score between 0.0 and 1.0
        """
        self._ensure_initialized()

        if not self.config.enabled:
            # Quality system disabled, return neutral score
            return 0.5

        # Try tiers in order based on configuration
        provider_used = None
        score = None

        # Tier 1: Local ONNX (if available)
        if self.config.ai_provider in ['local', 'auto'] and self._onnx_ranker:
            try:
                score = self._onnx_ranker.score_quality(query, memory.content)
                provider_used = 'onnx_local'
                logger.debug(f"Local ONNX score: {score:.3f}")
            except Exception as e:
                logger.warning(f"ONNX scoring failed: {e}")
                score = None

        # Tier 2: Groq API (if available and ONNX failed or in auto mode)
        if score is None and self.config.can_use_groq and self._groq_bridge:
            try:
                score = await self._score_with_groq(query, memory)
                provider_used = 'groq'
                logger.debug(f"Groq score: {score:.3f}")
            except Exception as e:
                logger.warning(f"Groq scoring failed: {e}")
                score = None

        # Tier 3: Gemini API (if available and previous tiers failed)
        if score is None and self.config.can_use_gemini:
            try:
                score = await self._score_with_gemini(query, memory)
                provider_used = 'gemini'
                logger.debug(f"Gemini score: {score:.3f}")
            except Exception as e:
                logger.warning(f"Gemini scoring failed: {e}")
                score = None

        # Tier 4: Implicit signals (always available as fallback)
        if score is None:
            score = self._implicit_evaluator.evaluate_quality(memory, query)
            provider_used = 'implicit_signals'
            logger.debug(f"Implicit signals score: {score:.3f}")

        # Store provider information in memory metadata
        memory.metadata['quality_provider'] = provider_used

        return score

    async def _score_with_groq(self, query: str, memory: Memory) -> float:
        """
        Score quality using Groq API.

        Args:
            query: Search query
            memory: Memory to score

        Returns:
            Quality score between 0.0 and 1.0
        """
        if not self._groq_bridge:
            raise RuntimeError("Groq bridge not initialized")

        prompt = self._create_scoring_prompt(query, memory.content)

        # Use fast model for quality scoring
        result = self._groq_bridge.call_model(
            prompt=prompt,
            model="llama-3.3-70b-versatile",
            max_tokens=50,
            temperature=0.1,
            system_message="You are a quality scorer. Respond only with a number between 0.0 and 1.0."
        )

        if result["status"] != "success":
            raise RuntimeError(f"Groq API error: {result.get('error', 'Unknown error')}")

        # Parse score from response
        response_text = result["response"].strip()
        try:
            score = float(response_text)
            return max(0.0, min(1.0, score))
        except ValueError:
            logger.warning(f"Could not parse Groq score: {response_text}")
            raise ValueError(f"Invalid score format: {response_text}")

    async def _score_with_gemini(self, query: str, memory: Memory) -> float:
        """
        Score quality using Gemini API.

        Args:
            query: Search query
            memory: Memory to score

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Placeholder for Gemini integration
        # This would use Gemini CLI or API similar to Groq
        logger.warning("Gemini scoring not yet implemented")
        raise NotImplementedError("Gemini scoring tier not yet implemented")

    def _create_scoring_prompt(self, query: str, memory_content: str) -> str:
        """
        Create a prompt for AI-based quality scoring.

        Args:
            query: Search query
            memory_content: Memory content to score

        Returns:
            Formatted prompt for AI model
        """
        return f"""Rate the relevance and quality of this memory for the given query.
Respond only with a number between 0.0 (completely irrelevant/low quality) and 1.0 (highly relevant/high quality).

Query: {query}

Memory: {memory_content[:500]}

Score:"""
