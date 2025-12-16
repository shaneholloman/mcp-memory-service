#!/usr/bin/env python3
"""
Graph Table Backfill Script

Migrates existing association memories to the memory_graph table for graph-based queries.
Run with --dry-run to preview changes before executing.

⚠️ IMPORTANT SAFETY NOTES:
- Creates automatic backup before execution
- Stop HTTP server before running: systemctl --user stop mcp-memory-http.service
- Disconnect MCP clients (use /mcp in Claude Code)
- Database must not be locked or in use

Usage:
    python backfill_graph_table.py --dry-run      # Preview changes (safe)
    python backfill_graph_table.py --apply        # Execute backfill
    python backfill_graph_table.py --apply --batch-size 200  # Custom batch size
"""

import sqlite3
import sys
import os
import subprocess
import shutil
import json
import asyncio
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp_memory_service.storage.graph import GraphStorage
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
    """Perform all safety checks before backfill."""
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
        if free_space < db_size * 2:  # Need at least 2x database size
            print(f"⚠️  Low disk space: {free_space / 1024**2:.1f} MB free, need {db_size * 2 / 1024**2:.1f} MB")
            all_passed = False
        else:
            print(f"✓ Sufficient disk space: {free_space / 1024**2:.1f} MB free")
    except Exception as e:
        print(f"⚠️  Could not check disk space: {e}")
        all_passed = False

    # Check 5: Graph table exists (create if missing)
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_graph'")
        result = cursor.fetchone()

        if not result:
            print("⚠️  memory_graph table does not exist - will create it")
        else:
            print("✓ memory_graph table exists")

        conn.close()
    except Exception as e:
        print(f"❌ Failed to check for memory_graph table: {e}")
        all_passed = False

    print("="*80)

    return all_passed


def ensure_graph_table_exists(conn: sqlite3.Connection) -> bool:
    """Ensure memory_graph table exists, create if missing."""
    try:
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_graph'")
        result = cursor.fetchone()

        if result:
            return True  # Table already exists

        print("\n📋 Creating memory_graph table...")

        # Create table with schema from migration 008
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_graph (
                source_hash TEXT NOT NULL,
                target_hash TEXT NOT NULL,
                similarity REAL NOT NULL,
                connection_types TEXT NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL,
                PRIMARY KEY (source_hash, target_hash)
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_source ON memory_graph(source_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_target ON memory_graph(target_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_bidirectional ON memory_graph(source_hash, target_hash)")

        conn.commit()

        print("✓ memory_graph table created successfully")
        return True

    except Exception as e:
        print(f"❌ Failed to create memory_graph table: {e}")
        return False


def fetch_association_memories(conn: sqlite3.Connection) -> List[Dict]:
    """Fetch all association memories from the database."""
    cursor = conn.cursor()

    # Query for association memories with discovered tag
    cursor.execute("""
        SELECT content, metadata, created_at
        FROM memories
        WHERE tags LIKE '%association%'
          AND tags LIKE '%discovered%'
    """)

    results = cursor.fetchall()
    associations = []

    for content, metadata_str, created_at in results:
        try:
            metadata = json.loads(metadata_str) if metadata_str else {}

            # Validate required fields
            if not all(key in metadata for key in ['source_memory_hashes', 'similarity_score']):
                print(f"⚠️  Skipping association with missing metadata fields")
                continue

            source_hashes = metadata.get('source_memory_hashes', [])
            if len(source_hashes) != 2:
                print(f"⚠️  Skipping association with {len(source_hashes)} hashes (expected 2)")
                continue

            # Extract connection types
            connection_type_str = metadata.get('connection_type', 'unknown')
            connection_types = [t.strip() for t in connection_type_str.split(',')]

            associations.append({
                'source_hash': source_hashes[0],
                'target_hash': source_hashes[1],
                'similarity': metadata.get('similarity_score', 0.0),
                'connection_types': connection_types,
                'metadata': {
                    'discovery_method': metadata.get('discovery_method', 'unknown'),
                    'discovery_date': metadata.get('discovery_date'),
                    'shared_concepts': metadata.get('shared_concepts', []),
                    'temporal_relationship': metadata.get('temporal_relationship'),
                    'confidence_score': metadata.get('confidence_score', 0.0),
                },
                'created_at': created_at
            })
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"⚠️  Skipping malformed association: {e}")
            continue

    return associations


async def backfill_associations(
    graph_storage: GraphStorage,
    associations: List[Dict],
    batch_size: int = 100,
    dry_run: bool = True
) -> Dict[str, int]:
    """Backfill associations into graph table."""
    stats = {
        'total': len(associations),
        'inserted': 0,
        'skipped_duplicate': 0,
        'failed': 0
    }

    if dry_run:
        print("\n" + "="*80)
        print("DRY RUN MODE - No changes will be made")
        print("="*80 + "\n")

    # Process in batches
    for i in range(0, len(associations), batch_size):
        batch = associations[i:i + batch_size]

        for assoc in batch:
            source = assoc['source_hash']
            target = assoc['target_hash']

            if dry_run:
                # Check if association already exists
                existing = await graph_storage.get_association(source, target)
                if existing:
                    stats['skipped_duplicate'] += 1
                else:
                    stats['inserted'] += 1
            else:
                # Check if already exists
                existing = await graph_storage.get_association(source, target)
                if existing:
                    stats['skipped_duplicate'] += 1
                    continue

                # Insert association
                success = await graph_storage.store_association(
                    source_hash=source,
                    target_hash=target,
                    similarity=assoc['similarity'],
                    connection_types=assoc['connection_types'],
                    metadata=assoc['metadata'],
                    created_at=assoc['created_at']
                )

                if success:
                    stats['inserted'] += 1
                else:
                    stats['failed'] += 1
                    print(f"❌ Failed to insert: {source[:8]} ↔ {target[:8]}")

        # Progress update
        progress = min(i + batch_size, len(associations))
        pct = (progress / len(associations)) * 100
        print(f"Progress: {progress}/{len(associations)} [{pct:.0f}%]", end='\r')

    print()  # New line after progress
    return stats


def display_sample_associations(associations: List[Dict], limit: int = 5):
    """Display sample associations for preview."""
    print("\n📊 Sample associations:")
    for assoc in associations[:limit]:
        source_short = assoc['source_hash'][:8]
        target_short = assoc['target_hash'][:8]
        similarity = assoc['similarity']
        types = ', '.join(assoc['connection_types'])
        print(f"  - {source_short} ↔ {target_short} (similarity: {similarity:.2f}, types: {types})")

    remaining = len(associations) - limit
    if remaining > 0:
        print(f"  ... and {remaining:,} more")


async def async_main(args):
    """Async main execution."""
    dry_run = '--apply' not in args
    batch_size = 100

    # Parse batch size
    if '--batch-size' in args:
        idx = args.index('--batch-size')
        if idx + 1 < len(args):
            try:
                batch_size = int(args[idx + 1])
            except ValueError:
                print("❌ Invalid batch size value")
                return 1

    print(f"\nGraph Table Backfill Script v{VERSION}")
    print(f"Database: {DB_PATH}")
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE EXECUTION'}")
    print(f"Batch size: {batch_size}")
    print("="*80)

    # Perform safety checks
    if not perform_safety_checks(DB_PATH, dry_run):
        print("\n❌ Safety checks failed. Aborting.")
        return 1

    # Create backup (unless dry-run)
    if not dry_run:
        print("\nCreating backup...")
        try:
            backup_path = create_backup(DB_PATH, dry_run)
            if backup_path:
                print(f"✓ Backup created: {backup_path}")
                print(f"  Size: {backup_path.stat().st_size / 1024**2:.2f} MB")
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return 1

    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)

    try:
        # Ensure graph table exists
        if not ensure_graph_table_exists(conn):
            print("\n❌ Failed to create/verify graph table. Aborting.")
            return 1

        # Fetch association memories
        print("\n🔍 Scanning for association memories...")
        associations = fetch_association_memories(conn)

        if not associations:
            print("✅ No association memories found (already backfilled or none exist)")
            return 0

        print(f"✅ Found {len(associations):,} association memories")

        # Display samples
        display_sample_associations(associations)

        # Confirm if not dry-run
        if not dry_run:
            print("\n" + "="*80)
            response = input("\nProceed with backfill? (yes/no): ")
            if response.lower() != "yes":
                print("Backfill cancelled.")
                return 0

        # Initialize graph storage
        graph_storage = GraphStorage(str(DB_PATH))

        # Execute backfill
        print(f"\n🚀 Starting backfill ({'dry-run mode' if dry_run else 'live mode'})...")
        stats = await backfill_associations(graph_storage, associations, batch_size, dry_run)

        # Display results
        print("\n📈 Results:")
        print(f"  Total found: {stats['total']:,}")
        print(f"  Successfully inserted: {stats['inserted']:,}")
        print(f"  Skipped (duplicates): {stats['skipped_duplicate']:,}")
        print(f"  Failed: {stats['failed']:,}")

        if dry_run:
            print("\n✅ Dry-run complete. Use --apply to execute changes.")
        else:
            print("\n✅ Backfill complete!")

        # Close graph storage
        await graph_storage.close()

        return 0 if stats['failed'] == 0 else 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        return 1

    finally:
        conn.close()


def main():
    """Main entry point."""
    # Run async main
    return asyncio.run(async_main(sys.argv))


if __name__ == "__main__":
    sys.exit(main())
