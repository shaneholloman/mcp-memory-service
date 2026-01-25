#!/usr/bin/env python3
"""
Restore soft-deleted memories from production database.

This script restores memories that were accidentally deleted during test runs.
It excludes test memories (those with __test__ tag) to avoid restoring test data.

Usage:
    # Close Claude Desktop first to avoid database locks!
    python scripts/maintenance/restore_deleted_memories.py [--dry-run]
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service.config import SQLITE_VEC_PATH


def restore_deleted_memories(dry_run: bool = False):
    """
    Restore soft-deleted production memories.

    Args:
        dry_run: If True, only show what would be restored without making changes
    """
    print(f"Using database: {SQLITE_VEC_PATH}")
    print()

    # Use WAL mode and longer timeout for concurrent access
    conn = sqlite3.connect(str(SQLITE_VEC_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    cursor = conn.cursor()

    # Get current statistics
    print("=" * 70)
    print("CURRENT DATABASE STATUS")
    print("=" * 70)

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN deleted_at IS NOT NULL THEN 1 ELSE 0 END) as deleted
        FROM memories
    """)
    total, active, deleted = cursor.fetchone()
    print(f"Total memories:    {total:,}")
    print(f"Active memories:   {active:,}")
    print(f"Deleted memories:  {deleted:,}")
    print()

    # Count test memories that will stay deleted
    cursor.execute("""
        SELECT COUNT(*)
        FROM memories
        WHERE deleted_at IS NOT NULL
          AND tags LIKE '%__test__%'
    """)
    test_count = cursor.fetchone()[0]

    production_to_restore = deleted - test_count

    print(f"Test memories (will keep deleted):     {test_count:,}")
    print(f"Production memories (will restore):    {production_to_restore:,}")
    print()

    # Show sample of what will be restored
    if production_to_restore > 0:
        print("=" * 70)
        print("SAMPLE OF MEMORIES TO RESTORE (first 10)")
        print("=" * 70)

        cursor.execute("""
            SELECT
                substr(content, 1, 100) as preview,
                tags,
                created_at_iso,
                datetime(deleted_at, 'unixepoch', 'localtime') as deleted_time
            FROM memories
            WHERE deleted_at IS NOT NULL
              AND (tags IS NULL OR tags NOT LIKE '%__test__%')
            ORDER BY created_at DESC
            LIMIT 10
        """)

        for i, (preview, tags, created, deleted_time) in enumerate(cursor.fetchall(), 1):
            print(f"\n{i}. Created: {created}")
            print(f"   Deleted: {deleted_time}")
            if tags:
                print(f"   Tags: {tags[:80]}")
            print(f"   Preview: {preview}...")

        print()

    # Perform restore or dry run
    print("=" * 70)
    if dry_run:
        print("DRY RUN MODE - No changes will be made")
        print("=" * 70)
        print()
        print(f"Would restore {production_to_restore:,} production memories")
        print(f"Would keep {test_count:,} test memories deleted")
        print()
        print("To actually perform the restore, run:")
        print(f"  python {sys.argv[0]}")
    else:
        print("RESTORING MEMORIES")
        print("=" * 70)
        print()

        # Restore non-test memories
        cursor.execute("""
            UPDATE memories
            SET deleted_at = NULL
            WHERE deleted_at IS NOT NULL
              AND (tags IS NULL OR tags NOT LIKE '%__test__%')
        """)

        restored = cursor.rowcount
        conn.commit()

        print(f"✅ Successfully restored {restored:,} production memories")
        print()

        # Show final statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN deleted_at IS NULL THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN deleted_at IS NOT NULL THEN 1 ELSE 0 END) as deleted
            FROM memories
        """)
        total, active, deleted = cursor.fetchone()

        print("=" * 70)
        print("FINAL DATABASE STATUS")
        print("=" * 70)
        print(f"Total memories:    {total:,}")
        print(f"Active memories:   {active:,}")
        print(f"Deleted memories:  {deleted:,}")
        print()

        print("✅ Restore complete! You can now restart Claude Desktop.")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Restore soft-deleted memories from production database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Preview what would be restored (safe, no changes)
    python scripts/maintenance/restore_deleted_memories.py --dry-run

    # Actually restore the memories
    python scripts/maintenance/restore_deleted_memories.py

IMPORTANT: Close Claude Desktop before running this script to avoid database locks!
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be restored without making changes'
    )

    args = parser.parse_args()

    try:
        restore_deleted_memories(dry_run=args.dry_run)
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
