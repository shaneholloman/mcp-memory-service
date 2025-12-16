#!/usr/bin/env python3
"""
Association Memory Cleanup Script

Safely removes association memories after graph table migration to reclaim database storage.
Run with --dry-run to preview deletions before executing.

⚠️ IMPORTANT SAFETY NOTES:
- Only deletes memories verified in graph table
- Creates automatic backup before execution
- Stop HTTP server before running: systemctl --user stop mcp-memory-http.service
- Disconnect MCP clients (use /mcp in Claude Code)
- Database must not be locked or in use
- Runs VACUUM to reclaim space after deletion

Usage:
    python cleanup_association_memories.py --dry-run      # Preview deletions (safe)
    python cleanup_association_memories.py                # Interactive cleanup
    python cleanup_association_memories.py --force        # Automated cleanup
    python cleanup_association_memories.py --force --batch-size 200  # Custom batch
"""

import sqlite3
import sys
import os
import subprocess
import shutil
import json
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp_memory_service.config import SQLITE_VEC_PATH

# Database path from application configuration
DB_PATH = Path(SQLITE_VEC_PATH) if SQLITE_VEC_PATH else None
if DB_PATH is None:
    print("❌ Error: SQLite database path not configured")
    print("   Ensure MCP_MEMORY_STORAGE_BACKEND is set to 'sqlite_vec' or 'hybrid'")
    sys.exit(1)

# Version
VERSION = "1.0.0"


def check_http_server_running() -> bool:
    """Check if HTTP server is running (Linux only)."""
    try:
        # Check systemd service
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "mcp-memory-http.service"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        # Not Linux or systemctl not available
        return False


def check_database_locked(db_path: Path) -> bool:
    """Check if database is currently locked."""
    try:
        # Try to open with a very short timeout
        conn = sqlite3.connect(db_path, timeout=0.1)
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        conn.rollback()
        conn.close()
        return False
    except sqlite3.OperationalError:
        return True


def create_backup(db_path: Path, dry_run: bool = False) -> Optional[Path]:
    """Create a timestamped backup of the database."""
    if dry_run:
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}.backup-{timestamp}{db_path.suffix}"

    try:
        shutil.copy2(db_path, backup_path)

        # Verify backup
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not created: {backup_path}")

        if backup_path.stat().st_size != db_path.stat().st_size:
            raise ValueError(f"Backup size mismatch: {backup_path.stat().st_size} != {db_path.stat().st_size}")

        return backup_path
    except Exception as e:
        print(f"\n❌ Error creating backup: {e}")
        raise


def perform_safety_checks(db_path: Path, dry_run: bool = False) -> bool:
    """Perform all safety checks before cleanup."""
    print("\n" + "="*80)
    print("Safety Checks")
    print("="*80)

    all_passed = True

    # Check 1: Database exists
    if not db_path.exists():
        print("❌ Database not found at:", db_path)
        return False
    print(f"✓ Database found: {db_path}")

    # Check 2: Database is not locked
    if check_database_locked(db_path):
        print("❌ Database is currently locked (in use by another process)")
        print("   Stop HTTP server: systemctl --user stop mcp-memory-http.service")
        print("   Disconnect MCP: Use /mcp command in Claude Code")
        all_passed = False
    else:
        print("✓ Database is not locked")

    # Check 3: HTTP server status (Linux only)
    if os.name != 'nt':  # Not Windows
        if check_http_server_running():
            print("⚠️  HTTP server is running")
            print("   Recommended: systemctl --user stop mcp-memory-http.service")
            if not dry_run:
                response = input("   Continue anyway? (yes/no): ")
                if response.lower() != "yes":
                    all_passed = False
        else:
            print("✓ HTTP server is not running")

    # Check 4: Sufficient disk space
    try:
        free_space = shutil.disk_usage(db_path.parent).free
        db_size = db_path.stat().st_size
        if free_space < db_size * 2:  # Need at least 2x database size for VACUUM
            print(f"⚠️  Low disk space: {free_space / 1024**2:.1f} MB free, need {db_size * 2 / 1024**2:.1f} MB")
            all_passed = False
        else:
            print(f"✓ Sufficient disk space: {free_space / 1024**2:.1f} MB free")
    except Exception as e:
        print(f"⚠️  Could not check disk space: {e}")
        all_passed = False

    # Check 5: Graph table exists
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_graph'")
        result = cursor.fetchone()

        if not result:
            print("❌ memory_graph table does not exist")
            print("   Run backfill_graph_table.py first to migrate associations")
            all_passed = False
        else:
            print("✓ memory_graph table exists")

            # Check if graph table is empty
            cursor.execute("SELECT COUNT(*) FROM memory_graph")
            count = cursor.fetchone()[0]
            if count == 0:
                print("⚠️  memory_graph table is empty (backfill not run or no associations)")
                if not dry_run:
                    response = input("   Continue anyway? (yes/no): ")
                    if response.lower() != "yes":
                        all_passed = False
            else:
                print(f"✓ memory_graph table has {count:,} associations")

        conn.close()
    except Exception as e:
        print(f"❌ Failed to check for memory_graph table: {e}")
        all_passed = False

    print("="*80)

    return all_passed


def fetch_association_memories(conn: sqlite3.Connection) -> List[Tuple[str, str, str]]:
    """
    Fetch all association memories from the database.

    Returns:
        List of (content_hash, content, metadata) tuples
    """
    cursor = conn.cursor()

    # Query for association memories with discovered tag
    cursor.execute("""
        SELECT content_hash, content, metadata
        FROM memories
        WHERE tags LIKE '%association%'
          AND tags LIKE '%discovered%'
    """)

    results = cursor.fetchall()
    associations = [(row[0], row[1], row[2]) for row in results]

    return associations


def verify_in_graph_table(conn: sqlite3.Connection, source_hash: str, target_hash: str) -> bool:
    """
    Verify that an association edge exists in the graph table.

    Args:
        conn: Database connection
        source_hash: Source memory content hash
        target_hash: Target memory content hash

    Returns:
        True if edge exists in graph table, False otherwise
    """
    cursor = conn.cursor()

    # Check if edge exists in either direction
    cursor.execute("""
        SELECT 1
        FROM memory_graph
        WHERE (source_hash = ? AND target_hash = ?)
           OR (source_hash = ? AND target_hash = ?)
        LIMIT 1
    """, (source_hash, target_hash, target_hash, source_hash))

    return cursor.fetchone() is not None


def get_graph_stats(conn: sqlite3.Connection) -> Dict[str, int]:
    """Get statistics about the graph table."""
    cursor = conn.cursor()

    # Total associations (bidirectional, so divide by 2)
    cursor.execute("SELECT COUNT(*) / 2 FROM memory_graph")
    total_associations = int(cursor.fetchone()[0])

    # Unique memory hashes in graph
    cursor.execute("""
        SELECT COUNT(DISTINCT source_hash)
        FROM memory_graph
    """)
    unique_memories = cursor.fetchone()[0]

    return {
        'total_associations': total_associations,
        'unique_memories': unique_memories
    }


def analyze_associations(
    conn: sqlite3.Connection,
    associations: List[Tuple[str, str, str]]
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """
    Analyze associations and categorize them.

    Returns:
        Tuple of (verified_list, orphaned_list)
        - verified: Associations found in graph table (safe to delete)
        - orphaned: Associations NOT in graph table (keep for safety)
    """
    verified = []
    orphaned = []

    print("\n🔍 Verifying associations in graph table...")

    for i, (content_hash, content, metadata_str) in enumerate(associations):
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"Progress: {i + 1}/{len(associations)} [{(i + 1) / len(associations) * 100:.0f}%]", end='\r')

        try:
            metadata = json.loads(metadata_str) if metadata_str else {}
            source_hashes = metadata.get('source_memory_hashes')

            if isinstance(source_hashes, list) and len(source_hashes) == 2:
                if verify_in_graph_table(conn, source_hashes[0], source_hashes[1]):
                    verified.append((content_hash, content))
                else:
                    orphaned.append((content_hash, content))
            else:
                # Malformed or missing source hashes
                orphaned.append((content_hash, content))
        except (json.JSONDecodeError, TypeError):
            orphaned.append((content_hash, content))

    print()  # New line after progress
    return verified, orphaned


def delete_memories(
    conn: sqlite3.Connection,
    memory_hashes: List[str],
    batch_size: int = 100,
    dry_run: bool = True
) -> Dict[str, int]:
    """
    Delete memories in batches with transaction safety.

    Args:
        conn: Database connection
        memory_hashes: List of content hashes to delete
        batch_size: Number of deletions per batch
        dry_run: If True, only count without deleting

    Returns:
        Stats dict with 'deleted', 'failed' counts
    """
    stats = {
        'deleted': 0,
        'failed': 0
    }

    if dry_run:
        print("\n" + "="*80)
        print("DRY RUN MODE - No changes will be made")
        print("="*80 + "\n")
        stats['deleted'] = len(memory_hashes)
        return stats

    cursor = conn.cursor()
    total = len(memory_hashes)

    try:
        # Begin transaction
        conn.execute("BEGIN TRANSACTION")

        # Process in batches
        for i in range(0, len(memory_hashes), batch_size):
            batch = memory_hashes[i:i + batch_size]

            for content_hash in batch:
                try:
                    cursor.execute("""
                        DELETE FROM memories
                        WHERE content_hash = ?
                    """, (content_hash,))

                    if cursor.rowcount > 0:
                        stats['deleted'] += 1
                    else:
                        stats['failed'] += 1
                        print(f"⚠️  Failed to delete: {content_hash[:8]} (not found)")

                except sqlite3.Error as e:
                    stats['failed'] += 1
                    print(f"❌ Error deleting {content_hash[:8]}: {e}")
                    continue

            # Progress update
            progress = min(i + batch_size, total)
            pct = (progress / total) * 100
            print(f"Progress: {progress}/{total} [{pct:.0f}%]", end='\r')

        print()  # New line after progress

        # Commit transaction
        conn.commit()
        print("\n✓ Transaction committed successfully")

    except Exception as e:
        # Rollback on error
        conn.rollback()
        print(f"\n❌ Error during deletion: {e}")
        print("✓ Transaction rolled back - no changes made")
        raise

    return stats


def run_vacuum(conn: sqlite3.Connection, dry_run: bool = False) -> bool:
    """
    Run VACUUM to reclaim database space.

    Args:
        conn: Database connection
        dry_run: If True, skip VACUUM

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print("\n(VACUUM would run here to reclaim space)")
        return True

    try:
        print("\n🗜️  Running VACUUM to reclaim space...")
        print("   This may take a minute for large databases...")

        # VACUUM cannot run in a transaction
        conn.execute("VACUUM")

        print("✓ VACUUM complete")
        return True

    except sqlite3.Error as e:
        print(f"❌ VACUUM failed: {e}")
        return False


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def main():
    """Main execution."""
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    batch_size = 100

    # Parse batch size
    if '--batch-size' in sys.argv:
        idx = sys.argv.index('--batch-size')
        if idx + 1 < len(sys.argv):
            try:
                batch_size = int(sys.argv[idx + 1])
            except ValueError:
                print("❌ Invalid batch size value")
                sys.exit(1)

    print(f"\nAssociation Memory Cleanup Script v{VERSION}")
    print(f"Database: {DB_PATH}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE EXECUTION' if not force else 'AUTOMATED EXECUTION (--force)'}")
    print(f"Batch size: {batch_size}")
    print("="*80)

    # Perform safety checks
    if not perform_safety_checks(DB_PATH, dry_run):
        print("\n❌ Safety checks failed. Aborting.")
        sys.exit(1)

    # Get database size before cleanup
    db_size_before = DB_PATH.stat().st_size
    print(f"\n📊 Database size before cleanup: {format_size(db_size_before)}")

    # Create backup (unless dry-run)
    if not dry_run:
        print("\nCreating backup...")
        try:
            backup_path = create_backup(DB_PATH, dry_run)
            if backup_path:
                print(f"✓ Backup created: {backup_path}")
                print(f"  Size: {format_size(backup_path.stat().st_size)}")
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)

    try:
        # Get graph table stats
        print("\n📈 Graph Table Statistics:")
        graph_stats = get_graph_stats(conn)
        print(f"  Total associations: {graph_stats['total_associations']:,}")
        print(f"  Unique memories: {graph_stats['unique_memories']:,}")

        # Fetch association memories
        print("\n🔍 Scanning for association memories...")
        associations = fetch_association_memories(conn)

        if not associations:
            print("✅ No association memories found (already cleaned up or none exist)")
            return 0

        print(f"✅ Found {len(associations):,} association memories")

        # Verify associations in graph table
        verified, orphaned = analyze_associations(conn, associations)

        print(f"\n📊 Verification Results:")
        print(f"  Verified in graph table: {len(verified):,} (safe to delete)")
        print(f"  Orphaned (not in graph): {len(orphaned):,} (will keep)")

        # Warn about count mismatch (expected due to metadata issues)
        if len(verified) != len(associations):
            delta = len(associations) - len(verified)
            print(f"\n⚠️  Note: {delta} memories not in graph table")
            print(f"   This is expected - some associations had incomplete metadata")
            print(f"   during migration and couldn't be backfilled.")

        # Warn if nothing to delete
        if len(verified) == 0:
            print("\n✅ No verified associations to delete (all orphaned or already cleaned)")
            return 0

        # Estimate space savings
        estimated_bytes_per_memory = 500  # Conservative estimate
        estimated_reclaim = len(verified) * estimated_bytes_per_memory
        print(f"\n💾 Estimated space reclaim: ~{format_size(estimated_reclaim)}")

        # Confirm if not dry-run and not force
        if not dry_run and not force:
            print("\n" + "="*80)
            print(f"\n⚠️  This will delete {len(verified):,} memories and reclaim ~{format_size(estimated_reclaim)}")
            print(f"   Orphaned memories ({len(orphaned):,}) will be preserved for safety")
            response = input("\nProceed with cleanup? (yes/no): ")
            if response.lower() != "yes":
                print("Cleanup cancelled.")
                return 0

        # Delete verified associations
        print(f"\n🗑️  Deleting {len(verified):,} verified association memories...")
        verified_hashes = [content_hash for content_hash, _ in verified]
        stats = delete_memories(conn, verified_hashes, batch_size, dry_run)

        # Display deletion results
        print("\n📈 Deletion Results:")
        print(f"  Successfully deleted: {stats['deleted']:,}")
        print(f"  Failed: {stats['failed']:,}")

        # Run VACUUM to reclaim space
        if not dry_run:
            vacuum_success = run_vacuum(conn, dry_run)
            if not vacuum_success:
                print("⚠️  VACUUM failed - space not reclaimed")

            # Get database size after cleanup
            db_size_after = DB_PATH.stat().st_size
            space_reclaimed = db_size_before - db_size_after
            pct_reduction = (space_reclaimed / db_size_before) * 100

            print(f"\n📊 Database size after cleanup: {format_size(db_size_after)}")
            print(f"   Space reclaimed: {format_size(space_reclaimed)} ({pct_reduction:.1f}% reduction)")

        if dry_run:
            print("\n✅ Dry-run complete. Run without --dry-run to execute changes.")
        else:
            print("\n✅ Cleanup complete!")
            if len(orphaned) > 0:
                print(f"\nℹ️  Note: {len(orphaned):,} orphaned associations were preserved")
                print(f"   These are memories not found in graph table (may have metadata issues)")

        return 0 if stats['failed'] == 0 else 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        return 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
