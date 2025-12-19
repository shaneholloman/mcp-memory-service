#!/usr/bin/env python3
"""
Hybrid Association Memory Cleanup Script

Removes association memories from BOTH local SQLite AND Cloudflare D1/Vectorize.
This ensures multi-PC sync doesn't restore deleted associations.

PROBLEM SOLVED:
    When using hybrid backend with multiple PCs, deleting association memories
    locally doesn't prevent them from being restored via Cloudflare drift-sync.
    The drift-sync mechanism (hybrid.py:632-750) pulls "missing" memories from
    Cloudflare back to local storage.

SOLUTION:
    Clean Cloudflare D1 FIRST, then local SQLite. This prevents sync from
    restoring deleted associations. Other PCs will sync the deletion automatically.

WORKFLOW:
    ┌─────────────┐     sync      ┌─────────────┐     sync      ┌─────────────┐
    │  Windows PC │ ◄──────────► │  Cloudflare │ ◄──────────► │  Linux PC   │
    │ (run here)  │              │  D1 + Vec   │              │  auto-sync  │
    └─────────────┘              └─────────────┘              └─────────────┘
           │                            │                            │
           └── 1. Delete D1 first ──────┘                            │
           └── 2. Delete Vectorize (optional) ───────────────────────┘
           └── 3. Delete local SQLite ───────────────────────────────┘

Usage:
    python cleanup_association_memories_hybrid.py --dry-run        # Preview
    python cleanup_association_memories_hybrid.py --apply          # Execute
    python cleanup_association_memories_hybrid.py --apply --skip-vectorize  # Skip Vectorize cleanup
    python cleanup_association_memories_hybrid.py --apply --cloudflare-only # Only clean Cloudflare
    python cleanup_association_memories_hybrid.py --apply --local-only      # Only clean local

Prerequisites:
    - MCP_GRAPH_STORAGE_MODE=graph_only should be set (v8.51.0+)
    - Graph table must exist (run backfill_graph_table.py first if needed)
    - Cloudflare credentials in environment (CLOUDFLARE_API_TOKEN, etc.)

See also:
    - cleanup_association_memories.py - Local-only cleanup (SQLite backend)
    - docs/migration/graph-migration-guide.md - Full migration guide
"""

import asyncio
import sqlite3
import os
import sys
import io
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Fix Windows console encoding FIRST
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Now import httpx
import httpx

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mcp_memory_service.config import SQLITE_VEC_PATH

# Database paths
DB_PATH = Path(SQLITE_VEC_PATH) if SQLITE_VEC_PATH else None

# Cloudflare config from environment
CF_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')
CF_ACCOUNT = os.getenv('CLOUDFLARE_ACCOUNT_ID')
CF_DATABASE = os.getenv('CLOUDFLARE_D1_DATABASE_ID')
CF_VECTORIZE = os.getenv('CLOUDFLARE_VECTORIZE_INDEX', 'mcp-memory-index')


async def get_cloudflare_associations() -> List[str]:
    """Get all association memory hashes from Cloudflare D1."""
    if not all([CF_TOKEN, CF_ACCOUNT, CF_DATABASE]):
        print("[ERROR] Cloudflare credentials not configured")
        return []
    
    headers = {
        'Authorization': f'Bearer {CF_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/d1/database/{CF_DATABASE}/query'
    
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json={
            'sql': "SELECT content_hash FROM memories WHERE content LIKE 'Association between%'"
        })
        data = resp.json()
        
        if not data.get('success'):
            print(f"[ERROR] Cloudflare query failed: {data}")
            return []
        
        results = data['result'][0]['results']
        hashes = [r['content_hash'] for r in results]
        print(f"[CLOUDFLARE] Found {len(hashes)} association memories")
        return hashes


async def delete_from_cloudflare_d1(hashes: List[str], batch_size: int = 50, dry_run: bool = True) -> int:
    """Delete memories from Cloudflare D1 database."""
    if dry_run:
        print(f"[DRY RUN] Would delete {len(hashes)} memories from Cloudflare D1")
        return len(hashes)
    
    if not all([CF_TOKEN, CF_ACCOUNT, CF_DATABASE]):
        print("[ERROR] Cloudflare credentials not configured")
        return 0
    
    headers = {
        'Authorization': f'Bearer {CF_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/d1/database/{CF_DATABASE}/query'
    deleted = 0
    
    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(hashes), batch_size):
            batch = hashes[i:i + batch_size]
            placeholders = ','.join(['?' for _ in batch])
            
            resp = await client.post(url, headers=headers, json={
                'sql': f"DELETE FROM memories WHERE content_hash IN ({placeholders})",
                'params': batch
            })
            
            data = resp.json()
            if data.get('success'):
                changes = data['result'][0].get('meta', {}).get('changes', len(batch))
                deleted += changes
                print(f"  D1: Deleted batch {i//batch_size + 1} ({changes} records)")
            else:
                print(f"  [ERROR] D1 batch delete failed: {data.get('errors', data)}")
            
            await asyncio.sleep(0.5)
    
    print(f"[OK] Deleted {deleted} memories from Cloudflare D1")
    return deleted


async def delete_from_cloudflare_vectorize(hashes: List[str], batch_size: int = 100, dry_run: bool = True) -> int:
    """Delete vectors from Cloudflare Vectorize.

    Note: This step is OPTIONAL. Orphaned vectors in Vectorize are harmless -
    they don't appear in search results since the D1 metadata is deleted.
    Use --skip-vectorize to skip this step if Vectorize API is problematic.

    Args:
        hashes: List of content hashes (vector IDs) to delete
        batch_size: Number of vectors to delete per API call
        dry_run: If True, only preview without actual deletion

    Returns:
        Number of vectors deleted (or would be deleted in dry-run mode)
    """
    if dry_run:
        print(f"[DRY RUN] Would delete {len(hashes)} vectors from Cloudflare Vectorize")
        return len(hashes)

    if not all([CF_TOKEN, CF_ACCOUNT]):
        print("[ERROR] Cloudflare credentials not configured")
        return 0

    headers = {
        'Authorization': f'Bearer {CF_TOKEN}',
        'Content-Type': 'application/json'
    }

    url = f'https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT}/vectorize/v2/indexes/{CF_VECTORIZE}/delete-by-ids'
    deleted = 0
    errors_count = 0

    async with httpx.AsyncClient(timeout=120) as client:
        for i in range(0, len(hashes), batch_size):
            batch = hashes[i:i + batch_size]

            try:
                resp = await client.post(url, headers=headers, json={
                    'ids': batch
                })

                # Handle non-JSON responses (Vectorize API can return HTML errors)
                try:
                    data = resp.json()
                except Exception as json_err:
                    errors_count += 1
                    if errors_count <= 3:  # Only show first few errors
                        print(f"  [WARN] Vectorize batch {i//batch_size + 1}: Invalid JSON response (HTTP {resp.status_code})")
                    continue

                if data.get('success'):
                    count = data.get('result', {}).get('count', len(batch))
                    deleted += count
                    print(f"  Vectorize: Deleted batch {i//batch_size + 1} ({count} vectors)")
                else:
                    errors = data.get('errors', [])
                    # Ignore "not found" errors - vectors may already be deleted
                    if errors and 'not found' not in str(errors).lower():
                        errors_count += 1
                        if errors_count <= 3:
                            print(f"  [WARN] Vectorize batch {i//batch_size + 1}: {errors}")

            except httpx.RequestError as e:
                errors_count += 1
                if errors_count <= 3:
                    print(f"  [WARN] Vectorize batch {i//batch_size + 1}: Network error - {e}")

            await asyncio.sleep(0.5)

    if errors_count > 3:
        print(f"  [WARN] {errors_count} total Vectorize errors (showing first 3)")

    print(f"[OK] Deleted {deleted} vectors from Cloudflare Vectorize")
    if errors_count > 0:
        print(f"     (Note: {errors_count} batches had errors - orphaned vectors are harmless)")
    return deleted


def get_local_associations(conn: sqlite3.Connection) -> List[str]:
    """Get all association memory hashes from local SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT content_hash FROM memories WHERE content LIKE 'Association between%'")
    hashes = [row[0] for row in cursor.fetchall()]
    print(f"[LOCAL] Found {len(hashes)} association memories")
    return hashes


def delete_from_local(conn: sqlite3.Connection, hashes: List[str], dry_run: bool = True) -> int:
    """Delete memories from local SQLite database."""
    if dry_run:
        print(f"[DRY RUN] Would delete {len(hashes)} memories from local SQLite")
        return len(hashes)
    
    cursor = conn.cursor()
    deleted = 0
    
    try:
        conn.execute("BEGIN TRANSACTION")
        
        for content_hash in hashes:
            cursor.execute("DELETE FROM memories WHERE content_hash = ?", (content_hash,))
            if cursor.rowcount > 0:
                deleted += 1
        
        conn.commit()
        print(f"[OK] Deleted {deleted} memories from local SQLite")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Local delete failed: {e}")
        raise
    
    return deleted


def create_backup(db_path: Path) -> Path:
    """Create a timestamped backup of the local database."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}.backup-{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    print(f"[BACKUP] Created: {backup_path}")
    return backup_path


def verify_graph_table(conn: sqlite3.Connection) -> Dict[str, int]:
    """Verify graph table has the association data."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM memory_graph")
        graph_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]
        
        return {
            'graph_edges': graph_count,
            'total_memories': memory_count,
            'graph_exists': graph_count > 0
        }
    except sqlite3.OperationalError:
        return {
            'graph_edges': 0,
            'total_memories': 0,
            'graph_exists': False,
            'error': 'Graph table does not exist!'
        }


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Hybrid Association Memory Cleanup - Cleans BOTH Cloudflare AND local SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run                    # Preview what would be deleted
  %(prog)s --apply                      # Execute full cleanup (D1 + Vectorize + local)
  %(prog)s --apply --skip-vectorize     # Skip Vectorize (orphaned vectors are harmless)
  %(prog)s --apply --cloudflare-only    # Only clean Cloudflare (run from any PC)
  %(prog)s --apply --local-only         # Only clean local (if Cloudflare already done)

Multi-PC Usage:
  For multi-PC setups, Cloudflare must be cleaned FIRST to prevent drift-sync
  from restoring deleted associations. Run with --cloudflare-only from one PC,
  then other PCs will auto-sync the deletion.
        """
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--apply', action='store_true', help='Apply changes (required for actual deletion)')
    parser.add_argument('--local-only', action='store_true', help='Only clean local SQLite (skip Cloudflare)')
    parser.add_argument('--cloudflare-only', action='store_true', help='Only clean Cloudflare (skip local SQLite)')
    parser.add_argument('--skip-vectorize', action='store_true',
                        help='Skip Vectorize cleanup (orphaned vectors are harmless and cleanup can fail)')
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.print_help()
        print("\nError: Specify --dry-run to preview or --apply to execute.")
        sys.exit(1)
    
    dry_run = args.dry_run
    
    print("=" * 70)
    print("HYBRID ASSOCIATION MEMORY CLEANUP")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (preview)' if dry_run else 'APPLY (destructive)'}")
    print()
    
    # Check local database
    if DB_PATH is None:
        print("[ERROR] Local database path not configured")
        sys.exit(1)
    
    if not DB_PATH.exists():
        print(f"[ERROR] Local database not found: {DB_PATH}")
        sys.exit(1)
    
    print(f"Local DB: {DB_PATH}")
    print(f"Cloudflare: {CF_DATABASE[:16]}... (Vectorize: {CF_VECTORIZE})")
    print()
    
    # Connect to local database
    conn = sqlite3.connect(DB_PATH)
    
    # Verify graph table exists
    graph_status = verify_graph_table(conn)
    print(f"Graph table status:")
    print(f"  - Graph edges: {graph_status['graph_edges']}")
    print(f"  - Total memories: {graph_status['total_memories']}")
    
    if not graph_status['graph_exists']:
        print("\n[ABORT] Graph table does not exist!")
        print("   Run backfill_graph_table.py first to migrate associations.")
        conn.close()
        sys.exit(1)
    
    # Get association counts
    print("\n--- Current State ---")
    local_hashes = get_local_associations(conn)
    cf_hashes = await get_cloudflare_associations()
    
    # Find unique hashes (union of both)
    all_hashes = list(set(local_hashes + cf_hashes))
    print(f"   Combined unique: {len(all_hashes)}")
    
    if len(all_hashes) == 0:
        print("\n[OK] No association memories to clean up!")
        conn.close()
        return
    
    # Confirmation for apply mode
    if not dry_run:
        print("\n[WARNING] This will permanently delete association memories from:")
        if not args.cloudflare_only:
            print(f"   - Local SQLite: {len(local_hashes)} memories")
        if not args.local_only:
            print(f"   - Cloudflare D1: {len(cf_hashes)} memories")
            if args.skip_vectorize:
                print(f"   - Cloudflare Vectorize: SKIPPED (--skip-vectorize)")
            else:
                print(f"   - Cloudflare Vectorize: {len(cf_hashes)} vectors")

        confirm = input("\nType 'yes' to proceed: ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            conn.close()
            return

        # Create backup
        if not args.cloudflare_only:
            create_backup(DB_PATH)
    
    # Execute cleanup
    print("\n--- Starting cleanup ---")
    stats = {
        'local_deleted': 0,
        'cf_d1_deleted': 0,
        'cf_vectorize_deleted': 0
    }
    
    # Cloudflare first (so sync doesn't bring them back)
    if not args.local_only and cf_hashes:
        print("\n[CLOUDFLARE CLEANUP]")
        stats['cf_d1_deleted'] = await delete_from_cloudflare_d1(cf_hashes, dry_run=dry_run)
        if args.skip_vectorize:
            print("  Vectorize: Skipped (--skip-vectorize flag)")
            stats['cf_vectorize_deleted'] = 0
        else:
            stats['cf_vectorize_deleted'] = await delete_from_cloudflare_vectorize(cf_hashes, dry_run=dry_run)
    
    # Then local
    if not args.cloudflare_only and local_hashes:
        print("\n[LOCAL CLEANUP]")
        stats['local_deleted'] = delete_from_local(conn, local_hashes, dry_run=dry_run)
        
        # VACUUM to reclaim space
        if not dry_run:
            print("\n[VACUUM] Reclaiming space...")
            conn.execute("VACUUM")
            print("[OK] VACUUM complete")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    action = "would be " if dry_run else ""
    print(f"Local SQLite:         {stats['local_deleted']} memories {action}deleted")
    print(f"Cloudflare D1:        {stats['cf_d1_deleted']} memories {action}deleted")
    if args.skip_vectorize:
        print(f"Cloudflare Vectorize: SKIPPED (orphaned vectors are harmless)")
    else:
        print(f"Cloudflare Vectorize: {stats['cf_vectorize_deleted']} vectors {action}deleted")
    
    if dry_run:
        print("\n[TIP] Run with --apply to execute these changes")
    else:
        print("\n[OK] Cleanup complete!")
        print("   Other PCs will sync the deletion automatically.")
    
    # Verify final state
    final_status = verify_graph_table(conn)
    print(f"\n--- Final State ---")
    print(f"   Graph edges: {final_status['graph_edges']} (preserved)")
    print(f"   Total memories: {final_status['total_memories']}")
    
    conn.close()


if __name__ == '__main__':
    asyncio.run(main())
