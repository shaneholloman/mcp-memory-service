#!/usr/bin/env python3
"""
Memory Relationship Type Inference Engine

Analyzes memory pairs to determine appropriate relationship types based on:
1. Memory type combinations (e.g., decision + error → "fixes")
2. Content analysis (e.g., "fixed", "resolved" → "fixes")
3. Temporal patterns (sequential creation → "follows")
4. Semantic contradictions (opposing content → "contradicts")

This enables rich knowledge graphs with meaningful relationship types beyond "related".
"""

import re
import logging
from typing import Tuple, Optional, List
from datetime import datetime

from ..models.ontology import (
    get_parent_type,
    validate_memory_type,
    validate_relationship,
)

logger = logging.getLogger(__name__)


class RelationshipInferenceEngine:
    """
    Analyzes memory pairs to determine appropriate relationship types.

    Uses multi-factor analysis:
    1. Memory type hierarchy compatibility
    2. Content semantic analysis
    3. Temporal relationship detection
    4. Contradiction detection
    """

    # Content patterns for relationship detection
    PATTERNS = {
        "causation": [
            r"\bcaused?\b",
            r"\blead\s+to\b",
            r"\bresulted\s+in\b",
            r"\btriggered\b",
            r"\bgenerated\b",
        ],
        "resolution": [
            r"\bfixed?\b",
            r"\bresolve[ds]?\b",
            r"\bcorrected?\b",
            r"\bpatched?\b",
            r"\brepaired\b",
            r"\bhealed\b",
        ],
        "support": [
            r"\bsupports?\b",
            r"\benables?\b",
            r"\bfacilitate[ds]?\b",
            r"\bhelps?\b",
            r"\baccompany\b",
        ],
        "contradiction": [
            r"\bcontradict[ds]?\b",
            r"\bconflict[ds]?\b",
            r"\bdisagree[ds]?\b",
            r"\bhowever\b",
            r"\b(but|yet|although|nevertheless)\b",
            r"\boppose[sd]?\b",
        ],
    }

    def __init__(self, min_confidence: float = 0.6):
        """
        Initialize the inference engine.

        Args:
            min_confidence: Minimum confidence score (0.0-1.0) to assign relationship type
        """
        self.min_confidence = min_confidence

    async def infer_relationship_type(
        self,
        source_type: Optional[str],
        target_type: Optional[str],
        source_content: str,
        target_content: str,
        source_timestamp: Optional[float] = None,
        target_timestamp: Optional[float] = None,
        source_tags: Optional[List[str]] = None,
        target_tags: Optional[List[str]] = None,
    ) -> Tuple[str, float]:
        """
        Infer relationship type between two memories.

        Args:
            source_type: Memory type of source memory
            target_type: Memory type of target memory
            source_content: Content of source memory
            target_content: Content of target memory
            source_timestamp: Creation timestamp of source memory (epoch)
            target_timestamp: Creation timestamp of target memory (epoch)
            source_tags: Tags on source memory
            target_tags: Tags on target memory

        Returns:
            Tuple of (relationship_type, confidence_score)

        Examples:
            >>> engine = RelationshipInferenceEngine()
            >>> result = await engine.infer_relationship_type(
            ...     source_type="learning/insight",
            ...     target_type="error/bug",
            ...     source_content="Fixed authentication issue...",
            ...     target_content="Authentication failed with timeout...",
            ...     source_timestamp=1234567890.0,
            ...     target_timestamp=1234560000.0
            ... )
            >>> result
            ("fixes", 0.85)
        """
        source_tags = source_tags or []
        target_tags = target_tags or []
        source_lower = source_content.lower()
        target_lower = target_content.lower()

        # Collect relationship type candidates with confidence scores
        candidates = []

        # 1. Analyze memory type combinations
        type_score = self._analyze_type_combination(source_type, target_type)
        if type_score:
            candidates.extend(type_score)

        # 2. Analyze content semantic patterns
        content_score = self._analyze_content_semantics(
            source_lower, target_lower, source_type, target_type
        )
        if content_score:
            candidates.extend(content_score)

        # 3. Analyze temporal relationships
        if source_timestamp and target_timestamp:
            temporal_score = self._analyze_temporal_relationship(
                source_timestamp, target_timestamp, source_type, target_type
            )
            if temporal_score:
                candidates.extend(temporal_score)

        # 4. Analyze contradictions
        contradiction_score = self._analyze_contradictions(
            source_lower,
            target_lower,
            source_type,
            target_type,
            source_tags,
            target_tags,
        )
        if contradiction_score:
            candidates.extend(contradiction_score)

        # Select highest-confidence candidate
        if not candidates:
            logger.debug(
                "No confident relationship type found, defaulting to 'related'"
            )
            return ("related", 0.0)

        # Sort by confidence descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_type, best_confidence = candidates[0]

        # Apply minimum confidence threshold
        if best_confidence < self.min_confidence:
            logger.debug(
                f"Confidence {best_confidence:.2f} below threshold {self.min_confidence}, "
                f"defaulting to 'related'"
            )
            return ("related", best_confidence)

        # Validate relationship type
        if not validate_relationship(best_type):
            logger.warning(f"Invalid relationship type inferred: {best_type}")
            return ("related", best_confidence)

        logger.debug(
            f"Inferred relationship type '{best_type}' with confidence {best_confidence:.2f}"
        )
        return (best_type, best_confidence)

    def _analyze_type_combination(
        self, source_type: Optional[str], target_type: Optional[str]
    ) -> List[Tuple[str, float]]:
        """
        Analyze memory type combinations to determine relationship type.

        Uses ontology-defined patterns:
        - decision → error → uses/causes
        - learning → error → fixes
        - decision → decision → supports/contradicts
        - etc.

        Returns:
            List of (relationship_type, confidence_score) candidates
        """
        if not source_type or not target_type:
            return []

        candidates = []
        source_parent = get_parent_type(source_type)
        target_parent = get_parent_type(target_type)

        # High-confidence patterns from ontology
        type_patterns = {
            ("decision", "error"): ("uses", 0.7),
            ("learning", "error"): ("fixes", 0.8),
            ("pattern", "error"): ("fixes", 0.75),
            ("learning", "decision"): ("supports", 0.6),
            ("observation", "learning"): ("supports", 0.5),
            ("pattern", "learning"): ("supports", 0.6),
            ("decision", "decision"): ("supports", 0.4),
            ("learning", "learning"): ("supports", 0.3),
            ("error", "error"): ("causes", 0.6),
            ("observation", "observation"): ("follows", 0.3),
        }

        # Check both (source, target) and (target, source) directions
        for (type1, type2), (rel_type, confidence) in type_patterns.items():
            if source_parent == type1 and target_parent == type2:
                candidates.append((rel_type, confidence))
            elif source_parent == type2 and target_parent == type1:
                # Reverse relationship - adjust confidence down
                candidates.append((rel_type, confidence * 0.7))

        return candidates

    def _analyze_content_semantics(
        self,
        source_lower: str,
        target_lower: str,
        source_type: Optional[str],
        target_type: Optional[str],
    ) -> List[Tuple[str, float]]:
        """
        Analyze content for semantic relationship patterns.

        Returns:
            List of (relationship_type, confidence_score) candidates
        """
        candidates = []

        # Check for resolution/fix patterns
        resolution_patterns = self.PATTERNS["resolution"]
        resolution_count = sum(
            1 for pattern in resolution_patterns if re.search(pattern, source_lower)
        )
        if resolution_count > 0:
            # If source contains resolution keywords and target is an error
            if target_type and "error" in target_type:
                confidence = min(0.9, 0.5 + (resolution_count * 0.1))
                candidates.append(("fixes", confidence))

        # Check for causation patterns
        causation_patterns = self.PATTERNS["causation"]
        causation_count = sum(
            1 for pattern in causation_patterns if re.search(pattern, source_lower)
        )
        if causation_count > 0:
            # If source contains causation keywords
            if target_type and "error" in target_type:
                confidence = min(0.8, 0.5 + (causation_count * 0.1))
                candidates.append(("causes", confidence))

        # Check for support patterns
        support_patterns = self.PATTERNS["support"]
        support_count = sum(
            1 for pattern in support_patterns if re.search(pattern, source_lower)
        )
        if support_count > 0:
            # If source contains support keywords
            if target_type and "decision" in target_type:
                confidence = min(0.75, 0.4 + (support_count * 0.1))
                candidates.append(("supports", confidence))

        return candidates

    def _analyze_temporal_relationship(
        self,
        source_timestamp: float,
        target_timestamp: float,
        source_type: Optional[str],
        target_type: Optional[str],
    ) -> List[Tuple[str, float]]:
        """
        Analyze temporal relationship between memories.

        Returns:
            List of (relationship_type, confidence_score) candidates
        """
        candidates = []

        # Calculate time difference
        time_diff = abs(source_timestamp - target_timestamp)

        # If created within 1 hour and same parent type
        if time_diff < 3600:
            source_parent = get_parent_type(source_type) if source_type else None
            target_parent = get_parent_type(target_type) if target_type else None

            if source_parent == target_parent:
                confidence = 0.4
                candidates.append(("follows", confidence))

        # If source created after target and describes fixing
        if (
            source_timestamp > target_timestamp
            and source_type
            and "learning" in source_type
        ):
            if target_type and "error" in target_type:
                confidence = 0.6
                candidates.append(("fixes", confidence))

        return candidates

    def _analyze_contradictions(
        self,
        source_lower: str,
        target_lower: str,
        source_type: Optional[str],
        target_type: Optional[str],
        source_tags: List[str],
        target_tags: List[str],
    ) -> List[Tuple[str, float]]:
        """
        Analyze potential contradictions between memories.

        Returns:
            List of (relationship_type, confidence_score) candidates
        """
        candidates = []

        # Check for contradiction keywords
        contradiction_patterns = self.PATTERNS["contradiction"]
        source_contradictions = sum(
            1 for pattern in contradiction_patterns if re.search(pattern, source_lower)
        )
        target_contradictions = sum(
            1 for pattern in contradiction_patterns if re.search(pattern, target_lower)
        )

        if source_contradictions > 0 or target_contradictions > 0:
            # High confidence if both have contradiction patterns
            if source_contradictions > 0 and target_contradictions > 0:
                confidence = 0.7
            else:
                confidence = 0.4

            candidates.append(("contradicts", confidence))

        return candidates


# Example usage
async def test_inference():
    """Test relationship type inference."""
    engine = RelationshipInferenceEngine(min_confidence=0.5)

    # Test 1: Learning fixes Error
    rel_type, confidence = await engine.infer_relationship_type(
        source_type="learning/insight",
        target_type="error/bug",
        source_content="Fixed authentication timeout by adjusting configuration",
        target_content="Authentication error: Request timeout after 30 seconds",
        source_timestamp=1234567890.0,
        target_timestamp=1234560000.0,
    )
    print(f"Test 1: {rel_type} (confidence: {confidence:.2f})")
    # Expected: "fixes" with high confidence

    # Test 2: Decision causes Error
    rel_type, confidence = await engine.infer_relationship_type(
        source_type="decision/architecture",
        target_type="error/bug",
        source_content="Chose to use HTTP instead of HTTPS for testing",
        target_content="HTTP connection refused: Port 8000 not responding",
        source_timestamp=1234567890.0,
        target_timestamp=1234567800.0,
    )
    print(f"Test 2: {rel_type} (confidence: {confidence:.2f})")
    # Expected: "causes" with moderate-high confidence

    # Test 3: Two decisions supporting each other
    rel_type, confidence = await engine.infer_relationship_type(
        source_type="decision/architecture",
        target_type="decision/tool_choice",
        source_content="Decided to use FastAPI for HTTP server",
        target_content="Chose ONNX for embeddings due to lightweight requirements",
        source_timestamp=1234567890.0,
        target_timestamp=1234567900.0,
    )
    print(f"Test 3: {rel_type} (confidence: {confidence:.2f})")
    # Expected: "supports" with moderate confidence

    # Test 4: Sequential observations
    rel_type, confidence = await engine.infer_relationship_type(
        source_type="observation",
        target_type="observation",
        source_content="Deployed version 9.0.0",
        target_content="Checked deployment status",
        source_timestamp=1234567890.0,
        target_timestamp=1234567950.0,
    )
    print(f"Test 4: {rel_type} (confidence: {confidence:.2f})")
    # Expected: "follows" with low-moderate confidence

    # Test 5: Default - no clear pattern
    rel_type, confidence = await engine.infer_relationship_type(
        source_type="observation",
        target_type="observation",
        source_content="Meeting notes about Q1 planning",
        target_content="Team lunch at Italian restaurant",
        source_timestamp=1234567890.0,
        target_timestamp=1234567000.0,
    )
    print(f"Test 5: {rel_type} (confidence: {confidence:.2f})")
    # Expected: "related" with low confidence


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_inference())
