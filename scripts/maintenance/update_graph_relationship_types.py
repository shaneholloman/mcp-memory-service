#!/usr/bin/env python3
"""
Batch Relationship Type Update Script

Enriches existing graph relationships with inferred relationship types.

This script:
1. Fetches all existing graph edges
2. Fetches the associated memories
3. Re-analyzes each pair with relationship inference engine
4. Updates `relationship_type` field with inferred type

Usage:
    python scripts/maintenance/update_graph_relationship_types.py [--dry-run] [--batch-size N]
"""

import argparse
import sqlite3
import sys
import json
import logging
from typing import List, Dict, Tuple
from datetime import datetime

# Add parent directory to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service.consolidation.relationship_inference import (
    RelationshipInferenceEngine,
)
from mcp_memory_service.models.memory import Memory
from mcp_memory_service.config import SQLITE_VEC_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RelationshipBatchUpdater:
    """Batch updater for existing graph relationships."""

    def __init__(self, db_path: str, min_confidence: float = 0.6):
        """
        Initialize batch updater.

        Args:
            db_path: Path to SQLite database
            min_confidence: Minimum confidence score (0.0-1.0) to assign relationship type
        """
        self.db_path = db_path
        self.min_confidence = min_confidence
        self.inference_engine = RelationshipInferenceEngine(
            min_confidence=min_confidence
        )
        self.conn = None

    def connect(self) -> sqlite3.Connection:
        """Connect to SQLite database."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def get_all_edges(self) -> List[Tuple]:
        """
        Fetch all edges from memory_graph table.

        Returns:
            List of (source_hash, target_hash, current_relationship_type, metadata)
        """
        conn = self.connect()

        query = """
            SELECT source_hash, target_hash, relationship_type, metadata
            FROM memory_graph
            WHERE relationship_type = 'related'
            ORDER BY created_at
        """
        cursor = conn.execute(query)
        return cursor.fetchall()

    def get_memories(self, hashes: List[str]) -> Dict[str, Memory]:
        """
        Fetch memories for given hashes.

        Args:
            hashes: List of memory content hashes

        Returns:
            Dict mapping hash -> Memory object
        """
        conn = self.connect()

        # Build placeholders list
        placeholders = ",".join("?" * len(hashes))

        query = f"""
            SELECT
                content_hash,
                content,
                memory_type,
                tags,
                created_at,
                updated_at,
                deleted_at
            FROM memories
            WHERE content_hash IN ({placeholders})
            AND deleted_at IS NULL
        """

        cursor = conn.execute(query, hashes)
        rows = cursor.fetchall()

        # Convert rows to Memory objects
        memories = {}
        for row in rows:
            # Parse tags safely
            tags = []
            if row["tags"]:
                try:
                    tags = json.loads(row["tags"])
                except:
                    try:
                        tags = eval(row["tags"])
                    except:
                        tags = []

            memory = Memory(
                content=row["content"],
                content_hash=row["content_hash"],
                memory_type=row["memory_type"] or "observation",
                tags=tags,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            memories[row["content_hash"]] = memory

        return memories

    def update_relationship_type(
        self, source_hash: str, target_hash: str, new_relationship_type: str
    ) -> bool:
        """
        Update relationship type for an edge.

        Args:
            source_hash: Source memory hash
            target_hash: Target memory hash
            new_relationship_type: New relationship type

        Returns:
            True if updated successfully
        """
        conn = self.connect()

        query = """
            UPDATE memory_graph
            SET relationship_type = ?
            WHERE source_hash = ?
              AND target_hash = ?
        """

        try:
            conn.execute(query, (new_relationship_type, source_hash, target_hash))
            conn.commit()
            return True
        except Exception as e:
            logger.error(
                f"Failed to update relationship {source_hash[:8]} -> {target_hash[:8]}: {e}"
            )
            conn.rollback()
            return False

    async def process_edges(
        self, dry_run: bool = False, batch_size: int = 100
    ) -> Dict[str, int]:
        """
        Process all edges and update relationship types.

        Args:
            dry_run: If True, don't make changes
            batch_size: Number of edges to process before commit

        Returns:
            Statistics dictionary
        """
        logger.info("Starting batch relationship type update")

        # Fetch all edges
        edges = self.get_all_edges()
        logger.info(f"Found {len(edges)} edges to process")

        # Collect all unique hashes
        all_hashes = set()
        for edge in edges:
            all_hashes.add(edge[0])  # source_hash
            all_hashes.add(edge[1])  # target_hash

        logger.info(f"Fetching {len(all_hashes)} unique memories...")

        # Fetch all memories in one query
        memory_map = self.get_memories(list(all_hashes))
        logger.info(f"Fetched {len(memory_map)} memories")

        # Process edges
        stats = {
            "total": len(edges),
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "no_memories": 0,
        }

        for i, (source_hash, target_hash, current_rel_type, metadata) in enumerate(
            edges, 1
        ):
            stats["processed"] += 1

            # Get memories
            source_memory = memory_map.get(source_hash)
            target_memory = memory_map.get(target_hash)

            if not source_memory or not target_memory:
                logger.warning(
                    f"Skipping edge {i}/{len(edges)} - missing memory data: "
                    f"{source_hash[:8]} <-> {target_hash[:8]}"
                )
                stats["no_memories"] += 1
                stats["skipped"] += 1
                continue

            # Infer relationship type
            try:
                (
                    inferred_rel,
                    confidence,
                ) = await self.inference_engine.infer_relationship_type(
                    source_type=source_memory.memory_type,
                    target_type=target_memory.memory_type,
                    source_content=source_memory.content,
                    target_content=target_memory.content,
                    source_timestamp=source_memory.created_at,
                    target_timestamp=target_memory.created_at,
                    source_tags=source_memory.tags,
                    target_tags=target_memory.tags,
                )
            except Exception as e:
                logger.error(f"Failed to infer relationship {i}/{len(edges)}: {e}")
                stats["failed"] += 1
                continue

            # Skip if no change
            if inferred_rel == current_rel_type:
                logger.debug(
                    f"Skipping edge {i}/{len(edges)} - no change needed: "
                    f"{current_rel_type} -> {inferred_rel}"
                )
                stats["skipped"] += 1
                continue

            # Update edge
            if dry_run:
                logger.info(
                    f"[DRY RUN] Would update edge {i}/{len(edges)}: "
                    f"{source_hash[:8]} <-> {target_hash[:8]} "
                    f"({current_rel_type} -> {inferred_rel}, confidence: {confidence:.2f})"
                )
                stats["updated"] += 1
            else:
                success = self.update_relationship_type(
                    source_hash, target_hash, inferred_rel
                )
                if success:
                    logger.info(
                        f"Updated edge {i}/{len(edges)}: "
                        f"{source_hash[:8]} <-> {target_hash[:8]} "
                        f"({current_rel_type} -> {inferred_rel}, confidence: {confidence:.2f})"
                    )
                    stats["updated"] += 1
                else:
                    stats["failed"] += 1

            # Progress update every 100 edges
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(edges)} edges...")

            # Periodic commit
            if i % batch_size == 0 and not dry_run:
                logger.info(f"Committing batch at {i} edges...")
                self.connect().commit()

        # Final commit
        if not dry_run:
            self.connect().commit()

        return stats

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def main():
    import asyncio

    parser = argparse.ArgumentParser(
        description="Batch update relationship types in knowledge graph"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without applying them"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of edges to process before commit (default: 100)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum confidence score (0.0-1.0, default: 0.6)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(SQLITE_VEC_PATH),
        help=f"Path to SQLite database (default: {SQLITE_VEC_PATH})",
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Batch Relationship Type Update Script")
    logger.info("=" * 70)
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Min confidence: {args.min_confidence}")
    logger.info("=" * 70)
    logger.info("")

    try:
        updater = RelationshipBatchUpdater(
            db_path=args.db_path, min_confidence=args.min_confidence
        )

        if args.dry_run:
            logger.info("⚠️  DRY RUN MODE - No changes will be made\n")

        stats = asyncio.run(
            updater.process_edges(dry_run=args.dry_run, batch_size=args.batch_size)
        )

        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total edges: {stats['total']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"No memories: {stats['no_memories']}")

        if args.dry_run:
            logger.info("")
            logger.info("⚠️  DRY RUN COMPLETE - Use without --dry-run to apply changes")

        logger.info("=" * 70)

        # Close connection
        updater.close()

        return 0

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
