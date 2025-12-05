"""Configuration for quality scoring system."""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityConfig:
    """Configuration for quality scoring system with local-first defaults."""

    # System control
    enabled: bool = True

    # AI provider selection
    # Options: 'local' (ONNX only), 'groq', 'gemini', 'auto' (try all), 'none' (implicit only)
    ai_provider: str = 'local'

    # Local ONNX model settings
    local_model: str = 'ms-marco-MiniLM-L-6-v2'
    local_device: str = 'auto'  # auto|cpu|cuda|mps|directml

    # Cloud API settings (optional, user opt-in)
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Quality boost (AI + implicit signals combination)
    boost_enabled: bool = False
    boost_weight: float = 0.3  # Weight for implicit signals when combining with AI

    @classmethod
    def from_env(cls) -> 'QualityConfig':
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv('MCP_QUALITY_SYSTEM_ENABLED', 'true').lower() == 'true',
            ai_provider=os.getenv('MCP_QUALITY_AI_PROVIDER', 'local'),
            local_model=os.getenv('MCP_QUALITY_LOCAL_MODEL', 'ms-marco-MiniLM-L-6-v2'),
            local_device=os.getenv('MCP_QUALITY_LOCAL_DEVICE', 'auto'),
            groq_api_key=os.getenv('GROQ_API_KEY'),
            gemini_api_key=os.getenv('GEMINI_API_KEY'),
            boost_enabled=os.getenv('MCP_QUALITY_BOOST_ENABLED', 'false').lower() == 'true',
            boost_weight=float(os.getenv('MCP_QUALITY_BOOST_WEIGHT', '0.3'))
        )

    def validate(self) -> bool:
        """Validate configuration settings."""
        if self.ai_provider not in ['local', 'groq', 'gemini', 'auto', 'none']:
            raise ValueError(f"Invalid ai_provider: {self.ai_provider}")

        if self.local_device not in ['auto', 'cpu', 'cuda', 'mps', 'directml']:
            raise ValueError(f"Invalid local_device: {self.local_device}")

        if not 0.0 <= self.boost_weight <= 1.0:
            raise ValueError(f"boost_weight must be between 0.0 and 1.0, got {self.boost_weight}")

        # Warn if cloud providers selected but no API keys
        if self.ai_provider == 'groq' and not self.groq_api_key:
            raise ValueError("Groq provider selected but GROQ_API_KEY not set")

        if self.ai_provider == 'gemini' and not self.gemini_api_key:
            raise ValueError("Gemini provider selected but GEMINI_API_KEY not set")

        return True

    @property
    def use_local_only(self) -> bool:
        """Check if using local-only scoring."""
        return self.ai_provider in ['local', 'none']

    @property
    def can_use_groq(self) -> bool:
        """Check if Groq API is available."""
        return self.groq_api_key is not None and self.ai_provider in ['groq', 'auto']

    @property
    def can_use_gemini(self) -> bool:
        """Check if Gemini API is available."""
        return self.gemini_api_key is not None and self.ai_provider in ['gemini', 'auto']
