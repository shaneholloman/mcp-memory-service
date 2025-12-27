# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Quality analytics processing utilities.

Extracted from server/handlers/quality.py Phase 3.4 refactoring to reduce
handle_analyze_quality_distribution complexity.
"""

import json
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class QualityDistributionAnalyzer:
    """Analyze quality score distribution across memories."""

    def __init__(self, memories: List[Any], min_quality: float = 0.0, max_quality: float = 1.0):
        """
        Initialize distribution analyzer.

        Args:
            memories: List of memory objects to analyze
            min_quality: Minimum quality score threshold (default: 0.0)
            max_quality: Maximum quality score threshold (default: 1.0)
        """
        self.memories = memories
        self.min_quality = min_quality
        self.max_quality = max_quality

        # Filter by quality range
        self.filtered_memories = self._filter_by_quality_range()

    def _filter_by_quality_range(self) -> List[Any]:
        """
        Filter memories by quality score range.

        Returns:
            List of memories within the quality range
        """
        filtered = []
        for memory in self.memories:
            quality_score = memory.metadata.get('quality_score', 0.5)
            if self.min_quality <= quality_score <= self.max_quality:
                filtered.append(memory)
        return filtered

    def get_statistics(self) -> Dict[str, Any]:
        """
        Calculate distribution statistics.

        Returns:
            Dict with total_memories, quality_scores, high/medium/low_quality lists, average_score
            Empty dict if no filtered memories
        """
        if not self.filtered_memories:
            return {}

        total_memories = len(self.filtered_memories)
        quality_scores = [m.metadata.get('quality_score', 0.5) for m in self.filtered_memories]

        # Categorize by quality tier
        high_quality = [m for m in self.filtered_memories if m.metadata.get('quality_score', 0.5) >= 0.7]
        medium_quality = [m for m in self.filtered_memories if 0.5 <= m.metadata.get('quality_score', 0.5) < 0.7]
        low_quality = [m for m in self.filtered_memories if m.metadata.get('quality_score', 0.5) < 0.5]

        average_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        return {
            "total_memories": total_memories,
            "quality_scores": quality_scores,
            "high_quality": high_quality,
            "medium_quality": medium_quality,
            "low_quality": low_quality,
            "average_score": average_score
        }

    def get_provider_breakdown(self) -> Dict[str, int]:
        """
        Get breakdown of memories by quality provider.

        Returns:
            Dict mapping provider names to memory counts
        """
        provider_counts = {}
        for memory in self.filtered_memories:
            provider = memory.metadata.get('quality_provider', 'implicit')
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
        return provider_counts


class QualityRankingProcessor:
    """Process quality rankings (top and bottom performers)."""

    @staticmethod
    def get_top_and_bottom(memories: List[Any], top_n: int = 10) -> Tuple[List[Any], List[Any]]:
        """
        Get top and bottom N memories by quality score.

        Args:
            memories: List of memory objects
            top_n: Number of top/bottom memories to return

        Returns:
            Tuple of (top_memories, bottom_memories)
        """
        sorted_memories = sorted(
            memories,
            key=lambda m: m.metadata.get('quality_score', 0.5),
            reverse=True
        )
        top_n_memories = sorted_memories[:top_n]
        bottom_n_memories = sorted_memories[-top_n:]

        return top_n_memories, bottom_n_memories


class QualityReportFormatter:
    """Format quality analytics results into human-readable report."""

    @staticmethod
    def format_distribution_report(
        total_memories: int,
        average_score: float,
        high_quality: List[Any],
        medium_quality: List[Any],
        low_quality: List[Any],
        provider_counts: Dict[str, int],
        top_10: List[Any],
        bottom_10: List[Any],
        min_quality: float,
        max_quality: float
    ) -> List[str]:
        """
        Format complete quality distribution report.

        Args:
            total_memories: Total number of memories analyzed
            average_score: Average quality score
            high_quality: List of high-quality memories (≥0.7)
            medium_quality: List of medium-quality memories (0.5-0.7)
            low_quality: List of low-quality memories (<0.5)
            provider_counts: Breakdown by quality provider
            top_10: Top 10 highest quality memories
            bottom_10: Bottom 10 lowest quality memories
            min_quality: Minimum quality threshold
            max_quality: Maximum quality threshold

        Returns:
            List of formatted report lines
        """
        response_lines = [
            "📊 Quality Score Distribution Analysis",
            "=" * 50,
            f"Total Memories: {total_memories}",
            f"Average Quality Score: {average_score:.3f}",
            "",
            "Distribution by Tier:",
            f"  🟢 High Quality (≥0.7): {len(high_quality)} ({len(high_quality)/total_memories*100:.1f}%)",
            f"  🟡 Medium Quality (0.5-0.7): {len(medium_quality)} ({len(medium_quality)/total_memories*100:.1f}%)",
            f"  🔴 Low Quality (<0.5): {len(low_quality)} ({len(low_quality)/total_memories*100:.1f}%)",
            "",
            "Provider Breakdown:"
        ]

        # Add provider breakdown
        for provider, count in sorted(provider_counts.items(), key=lambda x: x[1], reverse=True):
            response_lines.append(f"  {provider}: {count} ({count/total_memories*100:.1f}%)")

        # Add top performers
        response_lines.extend([
            "",
            "🏆 Top 10 Highest Quality Memories:"
        ])
        for i, memory in enumerate(top_10, 1):
            score = memory.metadata.get('quality_score', 0.5)
            content_preview = memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
            response_lines.append(f"  {i}. Score: {score:.3f} - {content_preview}")

        # Add bottom performers
        response_lines.extend([
            "",
            "⚠️  Bottom 10 Lowest Quality Memories:"
        ])
        for i, memory in enumerate(bottom_10, 1):
            score = memory.metadata.get('quality_score', 0.5)
            content_preview = memory.content[:60] + "..." if len(memory.content) > 60 else memory.content
            response_lines.append(f"  {i}. Score: {score:.3f} - {content_preview}")

        # Add JSON summary
        summary_data = {
            "total_memories": total_memories,
            "high_quality_count": len(high_quality),
            "medium_quality_count": len(medium_quality),
            "low_quality_count": len(low_quality),
            "average_score": round(average_score, 3),
            "provider_breakdown": provider_counts,
            "quality_range": {"min": min_quality, "max": max_quality}
        }

        response_lines.extend([
            "",
            "📋 JSON Summary:",
            json.dumps(summary_data, indent=2)
        ])

        return response_lines
