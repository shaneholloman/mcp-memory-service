#!/usr/bin/env python3
"""
Permanently delete tombstoned (soft-deleted) records from SQLite database.

This script performs a HARD DELETE of all soft-deleted records (deleted_at IS NOT NULL).
Data cannot be recovered after this operation.

Usage:
    # Preview what will be deleted (safe, dry-run mode)
    python scripts/maintenance/delete_tombstoned_records.py

    # Actually delete tombstoned records (PERMANENT)
    python scripts/maintenance/delete_tombstoned_records.py --delete

IMPORTANT: Close Claude Desktop before running to avoid database locks!
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service.config import SQLITE_VEC_PATH


def delete_tombstoned_records(dry_run: bool = True):
    """
    Permanently delete all tombstoned (soft-deleted) records.

    Args:
        dry_run: If True, only show what would be deleted without making changes
    """
    print(f"Using database: {SQLITE_VEC_PATH}")
    print()

    # Use WAL mode and longer timeout for concurrent access
    conn = sqlite3.connect(str(SQLITE_VEC_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    cursor = conn.cursor()

    print("=" * 70)
    print("TOMBSTONED RECORDS DELETION")
    print("=" * 70)
    print()

    # Get current stats
    cursor.execute("SELECT COUNT(*) FROM memories")
    total_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL")
    active = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM memories WHERE deleted_at IS NOT NULL")
    tombstoned = cursor.fetchone()[0]

    print(f"BEFORE DELETION:")
    print(f"  Total records:      {total_before:,}")
    print(f"  Active:             {active:,}")
    print(f"  Tombstoned:         {tombstoned:,}")
    print()

    if tombstoned == 0:
        print("✅ No tombstoned records found. Database is already clean.")
        conn.close()
        return

    # Show samples
    print("Sample of tombstoned records (first 10):")
    cursor.execute("""
        SELECT substr(content, 1, 80), tags, datetime(deleted_at, 'unixepoch', 'localtime')
        FROM memories
        WHERE deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
        LIMIT 10
    """)

    for content, tags, deleted_time in cursor.fetchall():
        print(f"  - Deleted: {deleted_time}")
        if tags:
            print(f"    Tags: {tags[:60]}")
        print(f"    Content: {content}...")
    print()

    if dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 70)
        print()
        print(f"Would permanently delete {tombstoned:,} tombstoned records")
        print()
        print("⚠️  WARNING: This is a PERMANENT deletion!")
        print("⚠️  Deleted records CANNOT be recovered!")
        print()
        print("To actually delete, run:")
        print(f"  python {sys.argv[0]} --delete")
    else:
        print("=" * 70)
        print("⚠️  PERMANENTLY DELETING TOMBSTONED RECORDS")
        print("=" * 70)
        print()

        # Delete from embeddings table first (if exists)
        try:
            cursor.execute("""
                DELETE FROM vec_memories
                WHERE content_hash IN (
                    SELECT content_hash FROM memories WHERE deleted_at IS NOT NULL
                )
            """)
            embedding_deleted = cursor.rowcount
            print(f"  Deleted {embedding_deleted:,} embeddings")
        except Exception as e:
            print(f"  No embeddings table or already cleaned: {e}")

        # Delete from associations/graph tables (if exist)
        try:
            cursor.execute("""
                DELETE FROM memory_associations
                WHERE source_hash IN (
                    SELECT content_hash FROM memories WHERE deleted_at IS NOT NULL
                )
                OR target_hash IN (
                    SELECT content_hash FROM memories WHERE deleted_at IS NOT NULL
                )
            """)
            assoc_deleted = cursor.rowcount
            print(f"  Deleted {assoc_deleted:,} associations")
        except Exception as e:
            print(f"  No associations table or already cleaned: {e}")

        # Delete tombstoned memories
        cursor.execute("DELETE FROM memories WHERE deleted_at IS NOT NULL")
        deleted = cursor.rowcount

        conn.commit()

        print(f"  Deleted {deleted:,} tombstoned memories")
        print()

        # VACUUM to reclaim space
        print("Running VACUUM to reclaim disk space...")
        cursor.execute("VACUUM")
        print("  ✅ VACUUM complete")
        print()

        # Final stats
        cursor.execute("SELECT COUNT(*) FROM memories")
        total_after = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL")
        active_after = cursor.fetchone()[0]

        print("=" * 70)
        print("AFTER DELETION:")
        print("=" * 70)
        print(f"  Total records:      {total_after:,}")
        print(f"  Active:             {active_after:,}")
        print(f"  Tombstoned:         0")
        print()
        print(f"✅ Successfully deleted {deleted:,} tombstoned records")
        print(f"✅ Database cleaned and optimized")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Permanently delete tombstoned (soft-deleted) records from database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be deleted (safe, no changes)
    python scripts/maintenance/delete_tombstoned_records.py

    # Actually delete tombstoned records (PERMANENT!)
    python scripts/maintenance/delete_tombstoned_records.py --delete

IMPORTANT: Close Claude Desktop before running this script to avoid database locks!

WARNING: This performs a PERMANENT deletion. Deleted records CANNOT be recovered.
        """
    )
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Actually delete tombstoned records (default: dry-run only)'
    )

    args = parser.parse_args()

    try:
        delete_tombstoned_records(dry_run=not args.delete)
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            print("\n❌ ERROR: Database is locked!")
            print()
            print("Please close Claude Desktop and any other applications using the database,")
            print("then try again.")
            print()
            print("Active processes using the database:")
            import subprocess
            try:
                result = subprocess.run(
                    ["lsof", str(SQLITE_VEC_PATH)],
                    capture_output=True,
                    text=True
                )
                if result.stdout:
                    print(result.stdout)
            except:
                pass
            sys.exit(1)
        else:
            raise


if __name__ == '__main__':
    main()
