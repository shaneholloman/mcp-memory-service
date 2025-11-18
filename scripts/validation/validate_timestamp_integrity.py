#!/usr/bin/env python3
"""
Timestamp Integrity Validation Script

Detects timestamp anomalies that could indicate the regression bug where
created_at timestamps were being reset during metadata sync operations.

Checks for:
1. Suspicious clusters of recent created_at timestamps
2. Created_at timestamps that are newer than they should be
3. Memories with identical or very similar created_at timestamps (indicating bulk reset)
4. created_at > updated_at (logically impossible)
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter
from typing import List, Dict, Tuple, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
import mcp_memory_service.config as config_module


class TimestampIntegrityValidator:
    """Validator for detecting timestamp integrity issues."""

    def __init__(self, storage):
        self.storage = storage
        self.warnings = []
        self.errors = []

    async def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """
        Run all timestamp integrity checks.

        Returns:
            Tuple of (is_healthy, warnings, errors)
        """
        print("🔍 Running timestamp integrity validation...\n")

        await self.check_impossible_timestamps()
        await self.check_suspicious_clusters()
        await self.check_future_timestamps()
        await self.check_timestamp_distribution()

        # Print summary
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)

        if not self.errors and not self.warnings:
            print("✅ No timestamp integrity issues detected!")
            return True, [], []

        if self.errors:
            print(f"\n❌ ERRORS: {len(self.errors)}")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  - {warning}")

        return len(self.errors) == 0, self.warnings, self.errors

    async def check_impossible_timestamps(self):
        """Check for logically impossible timestamps (created_at > updated_at)."""
        print("1️⃣ Checking for impossible timestamps (created_at > updated_at)...")

        if hasattr(self.storage, 'conn'):  # SQLite-vec
            cursor = self.storage.conn.execute('''
                SELECT content_hash, created_at, updated_at,
                       created_at_iso, updated_at_iso
                FROM memories
                WHERE created_at > updated_at
            ''')

            impossible = cursor.fetchall()

            if impossible:
                self.errors.append(
                    f"Found {len(impossible)} memories with created_at > updated_at (impossible!)"
                )
                for row in impossible[:5]:  # Show first 5
                    content_hash, created_at, updated_at, created_iso, updated_iso = row
                    print(f"   ❌ {content_hash[:8]}: created={created_iso}, updated={updated_iso}")
            else:
                print("   ✅ No impossible timestamps found")

        else:
            print("   ⚠️ Skipped (not SQLite backend)")

    async def check_suspicious_clusters(self):
        """Check for suspicious clusters of recent created_at timestamps."""
        print("\n2️⃣ Checking for suspicious timestamp clusters...")

        if hasattr(self.storage, 'conn'):  # SQLite-vec
            # Get all created_at timestamps
            cursor = self.storage.conn.execute('''
                SELECT created_at, created_at_iso, COUNT(*) as count
                FROM memories
                GROUP BY created_at
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            ''')

            clusters = cursor.fetchall()

            if clusters:
                # Check if there are large clusters (> 5 memories with same timestamp)
                large_clusters = [c for c in clusters if c[2] > 5]

                if large_clusters:
                    self.warnings.append(
                        f"Found {len(large_clusters)} suspicious timestamp clusters "
                        f"(multiple memories with identical created_at)"
                    )
                    print(f"   ⚠️  {len(large_clusters)} suspicious clusters found:")
                    for created_at, created_iso, count in large_clusters[:5]:
                        age_hours = (time.time() - created_at) / 3600
                        print(f"      - {count} memories at {created_iso} ({age_hours:.1f}h ago)")
                else:
                    print(f"   ✅ No suspicious clusters (some duplicates normal)")

            else:
                print("   ✅ No timestamp clusters found")

        else:
            print("   ⚠️ Skipped (not SQLite backend)")

    async def check_future_timestamps(self):
        """Check for timestamps in the future."""
        print("\n3️⃣ Checking for future timestamps...")

        now = time.time()
        future_threshold = now + 300  # 5 minutes tolerance

        if hasattr(self.storage, 'conn'):  # SQLite-vec
            cursor = self.storage.conn.execute('''
                SELECT content_hash, created_at, updated_at,
                       created_at_iso, updated_at_iso
                FROM memories
                WHERE created_at > ? OR updated_at > ?
            ''', (future_threshold, future_threshold))

            future_timestamps = cursor.fetchall()

            if future_timestamps:
                self.errors.append(
                    f"Found {len(future_timestamps)} memories with timestamps in the future!"
                )
                for row in future_timestamps[:5]:
                    content_hash, created_at, updated_at, created_iso, updated_iso = row
                    if created_at > future_threshold:
                        print(f"   ❌ {content_hash[:8]}: created_at in future: {created_iso}")
                    if updated_at > future_threshold:
                        print(f"   ❌ {content_hash[:8]}: updated_at in future: {updated_iso}")
            else:
                print("   ✅ No future timestamps found")

        else:
            print("   ⚠️ Skipped (not SQLite backend)")

    async def check_timestamp_distribution(self):
        """Check timestamp distribution for anomalies (e.g., all recent)."""
        print("\n4️⃣ Checking timestamp distribution...")

        if hasattr(self.storage, 'conn'):  # SQLite-vec
            # Get timestamp statistics
            cursor = self.storage.conn.execute('''
                SELECT
                    COUNT(*) as total,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest,
                    AVG(created_at) as avg_timestamp
                FROM memories
            ''')

            row = cursor.fetchone()
            if not row or row[0] == 0:
                print("   ℹ️  No memories to analyze")
                return

            total, oldest, newest, avg_timestamp = row

            # Calculate time ranges
            now = time.time()
            oldest_age_days = (now - oldest) / 86400
            newest_age_hours = (now - newest) / 3600

            print(f"   📈 Total memories: {total}")
            print(f"   📅 Oldest: {datetime.utcfromtimestamp(oldest).isoformat()}Z ({oldest_age_days:.1f} days ago)")
            print(f"   📅 Newest: {datetime.utcfromtimestamp(newest).isoformat()}Z ({newest_age_hours:.1f} hours ago)")

            # Check for anomaly: if > 50% of memories created in last 24 hours
            # but oldest is > 7 days old (indicates bulk timestamp reset)
            cursor = self.storage.conn.execute('''
                SELECT COUNT(*) FROM memories
                WHERE created_at > ?
            ''', (now - 86400,))

            recent_count = cursor.fetchone()[0]
            recent_percentage = (recent_count / total) * 100

            if recent_percentage > 50 and oldest_age_days > 7:
                self.warnings.append(
                    f"Suspicious: {recent_percentage:.1f}% of memories created in last 24h, "
                    f"but oldest memory is {oldest_age_days:.1f} days old. "
                    f"This could indicate timestamp reset bug!"
                )
                print(f"   ⚠️  {recent_percentage:.1f}% created in last 24h (suspicious if many old memories)")

            # Check distribution by age buckets
            buckets = [
                ("Last hour", 3600),
                ("Last 24 hours", 86400),
                ("Last week", 604800),
                ("Last month", 2592000),
                ("Older", float('inf'))
            ]

            print(f"\n   📊 Distribution by age:")
            for label, seconds in buckets:
                if seconds == float('inf'):
                    cursor = self.storage.conn.execute('''
                        SELECT COUNT(*) FROM memories
                        WHERE created_at < ?
                    ''', (now - 2592000,))
                else:
                    cursor = self.storage.conn.execute('''
                        SELECT COUNT(*) FROM memories
                        WHERE created_at > ?
                    ''', (now - seconds,))

                count = cursor.fetchone()[0]
                percentage = (count / total) * 100
                print(f"      {label:15}: {count:4} ({percentage:5.1f}%)")

        else:
            print("   ⚠️ Skipped (not SQLite backend)")


async def main():
    """Main validation function."""
    print("="*60)
    print("⏰ TIMESTAMP INTEGRITY VALIDATION")
    print("="*60)
    print()

    try:
        # Get database path from config
        storage_backend = os.getenv('MCP_MEMORY_STORAGE_BACKEND', 'sqlite_vec')
        db_path = config_module.MEMORY_SQLITE_DB_PATH

        print(f"Backend: {storage_backend}")
        print(f"Database: {db_path}")
        print()

        # Initialize storage
        storage = SqliteVecMemoryStorage(
            db_path=db_path,
            embedding_model="all-MiniLM-L6-v2"
        )
        await storage.initialize()

        # Run validation
        validator = TimestampIntegrityValidator(storage)
        is_healthy, warnings, errors = await validator.validate_all()

        # Close storage
        if hasattr(storage, 'close'):
            storage.close()

        # Exit with appropriate code
        if errors:
            print("\n❌ Validation FAILED with errors")
            sys.exit(1)
        elif warnings:
            print("\n⚠️  Validation completed with warnings")
            sys.exit(0)
        else:
            print("\n✅ Validation PASSED - Timestamps are healthy!")
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ Validation failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
