"""Data models for session harvest."""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional

HARVEST_TYPES = ["decision", "bug", "convention", "learning", "context"]

# Maximum characters for candidate content preview in MCP tool output
MAX_CANDIDATE_PREVIEW_LENGTH = 200


@dataclass
class HarvestCandidate:
    """A single extracted memory candidate."""
    content: str
    memory_type: str  # One of HARVEST_TYPES
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.5
    source_line: str = ""  # Original text that triggered extraction


@dataclass
class HarvestResult:
    """Result of a harvest operation."""
    candidates: List[HarvestCandidate]
    session_id: str
    total_messages: int
    found: int
    by_type: Dict[str, int]
    stored: int = 0  # Only set when dry_run=False


@dataclass
class HarvestConfig:
    """Configuration for harvest operation."""
    sessions: int = 1
    session_ids: Optional[List[str]] = None
    types: List[str] = field(default_factory=lambda: list(HARVEST_TYPES))
    min_confidence: float = 0.6
    dry_run: bool = True
    project_path: Optional[str] = None  # Override project dir
    use_llm: bool = False  # Phase 2: LLM-based classification
    # P4: Harvest evolution — evolve existing memories instead of duplicating
    similarity_threshold: float = 0.85  # Cosine similarity to trigger evolution
    min_confidence_to_evolve: float = 0.3  # Skip evolution for very stale memories


def harvest_config_from_env(**overrides) -> HarvestConfig:
    """Create HarvestConfig with environment variable overrides."""
    defaults = {}
    threshold = os.environ.get("MCP_HARVEST_SIMILARITY_THRESHOLD")
    if threshold is not None:
        defaults["similarity_threshold"] = float(threshold)
    min_conf = os.environ.get("MCP_HARVEST_MIN_CONFIDENCE_TO_EVOLVE")
    if min_conf is not None:
        defaults["min_confidence_to_evolve"] = float(min_conf)
    defaults.update(overrides)
    return HarvestConfig(**defaults)
