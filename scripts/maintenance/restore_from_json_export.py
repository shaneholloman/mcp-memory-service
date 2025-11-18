#!/usr/bin/env python3
"""
Restore Timestamps from Clean JSON Export

Recovers corrupted timestamps using the clean export from the other MacBook
(v8.26, before the hybrid sync bug). Matches memories by content_hash and
restores their original creation timestamps.

This script:
- Reads clean timestamp mapping (content_hash → ISO timestamp)
- Matches memories in current database by content_hash
- Updates created_at and created_at_iso with original timestamps
- Preserves memories not in mapping (created after the clean export)

Usage:
    python scripts/maintenance/restore_from_json_export.py [--dry-run|--apply]
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_memory_service import config


def restore_from_json(db_path: str, mapping_file: str, dry_run: bool = True):
    """
    Restore timestamps from JSON export mapping.

    Args:
        db_path: Path to SQLite database
        mapping_file: Path to JSON file with content_hash → timestamp mapping
        dry_run: If True, only show what would be changed
    """
    print("=" * 80)
    print("TIMESTAMP RESTORATION FROM CLEAN JSON EXPORT")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Mapping:  {mapping_file}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (applying changes)'}")
    print()

    # Load clean timestamp mapping
    print("Loading clean timestamp mapping...")
    with open(mapping_file, 'r') as f:
        clean_mapping = json.load(f)

    print(f"✅ Loaded {len(clean_mapping)} clean timestamps")
    print()

    # Connect to database
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute('PRAGMA busy_timeout = 30000')
    cursor = conn.cursor()

    # Get all memories from current database
    print("Analyzing current database...")
    cursor.execute('''
        SELECT content_hash, created_at, created_at_iso, substr(content, 1, 60)
        FROM memories
    ''')

    current_memories = cursor.fetchall()
    print(f"✅ Found {len(current_memories)} memories in database")
    print()

    # Match and analyze
    print("=" * 80)
    print("MATCHING ANALYSIS:")
    print("=" * 80)

    matched = []
    unmatched = []
    already_correct = []

    for content_hash, created_at, created_at_iso, content_preview in current_memories:
        if content_hash in clean_mapping:
            clean_timestamp = clean_mapping[content_hash]

            # Check if already correct
            if created_at_iso == clean_timestamp:
                already_correct.append(content_hash)
            else:
                matched.append({
                    'hash': content_hash,
                    'current_iso': created_at_iso,
                    'clean_iso': clean_timestamp,
                    'content': content_preview
                })
        else:
            unmatched.append({
                'hash': content_hash,
                'created_iso': created_at_iso,
                'content': content_preview
            })

    print(f"✅ Matched (will restore): {len(matched)}")
    print(f"✅ Already correct: {len(already_correct)}")
    print(f"⏭️  Unmatched (keep as-is): {len(unmatched)}")
    print()

    # Show samples
    print("=" * 80)
    print("SAMPLE RESTORATIONS (first 10):")
    print("=" * 80)
    for i, mem in enumerate(matched[:10], 1):
        print(f"{i}. Hash: {mem['hash'][:16]}...")
        print(f"   CURRENT: {mem['current_iso']}")
        print(f"   RESTORE: {mem['clean_iso']}")
        print(f"   Content: {mem['content']}...")
        print()

    if len(matched) > 10:
        print(f"   ... and {len(matched) - 10} more")
        print()

    # Show unmatched samples (new memories)
    if unmatched:
        print("=" * 80)
        print("UNMATCHED MEMORIES (will keep current timestamps):")
        print("=" * 80)
        print(f"Total: {len(unmatched)} memories")
        print("\nSample (first 5):")
        for i, mem in enumerate(unmatched[:5], 1):
            print(f"{i}. Hash: {mem['hash'][:16]}...")
            print(f"   Created: {mem['created_iso']}")
            print(f"   Content: {mem['content']}...")
            print()

    if dry_run:
        print("=" * 80)
        print("DRY RUN COMPLETE - No changes made")
        print("=" * 80)
        print(f"Would restore {len(matched)} timestamps")
        print(f"Would preserve {len(unmatched)} new memories")
        print("\nTo apply changes, run with --apply flag")
        conn.close()
        return

    # Confirm before proceeding
    print("=" * 80)
    print(f"⚠️  ABOUT TO RESTORE {len(matched)} TIMESTAMPS")
    print("=" * 80)
    response = input("Continue with restoration? [y/N]: ")

    if response.lower() != 'y':
        print("Restoration cancelled")
        conn.close()
        return

    # Apply restorations
    print("\nRestoring timestamps...")
    restored_count = 0
    failed_count = 0

    for mem in matched:
        try:
            content_hash = mem['hash']
            clean_iso = mem['clean_iso']

            # Convert ISO to Unix timestamp
            dt = datetime.fromisoformat(clean_iso.replace('Z', '+00:00'))
            clean_unix = dt.timestamp()

            # Update database
            cursor.execute('''
                UPDATE memories
                SET created_at = ?, created_at_iso = ?
                WHERE content_hash = ?
            ''', (clean_unix, clean_iso, content_hash))

            restored_count += 1

            if restored_count % 100 == 0:
                print(f"  Progress: {restored_count}/{len(matched)} restored...")
                conn.commit()  # Commit in batches

        except Exception as e:
            print(f"  Error restoring {content_hash[:16]}: {e}")
            failed_count += 1

    # Final commit
    conn.commit()

    # Verify results
    cursor.execute('''
        SELECT created_at_iso, COUNT(*) as count
        FROM memories
        GROUP BY DATE(created_at_iso)
        ORDER BY DATE(created_at_iso) DESC
        LIMIT 20
    ''')

    print()
    print("=" * 80)
    print("RESTORATION COMPLETE")
    print("=" * 80)
    print(f"✅ Successfully restored: {restored_count}")
    print(f"❌ Failed to restore: {failed_count}")
    print(f"⏭️  Preserved (new memories): {len(unmatched)}")
    print()

    # Show date distribution
    print("=" * 80)
    print("TIMESTAMP DISTRIBUTION (After Restoration):")
    print("=" * 80)

    from collections import Counter
    cursor.execute('SELECT created_at_iso FROM memories')
    dates = Counter()
    for row in cursor.fetchall():
        date_str = row[0][:10] if row[0] else 'Unknown'
        dates[date_str] += 1

    for date, count in dates.most_common(15):
        print(f"  {date}: {count:4} memories")

    # Check corruption remaining
    corruption_dates = {'2025-11-16', '2025-11-17', '2025-11-18'}
    corrupted_remaining = sum(count for date, count in dates.items() if date in corruption_dates)

    print()
    print(f"Corrupted dates remaining: {corrupted_remaining}")
    print(f"Expected: ~250-400 (legitimately created Nov 16-18)")

    conn.close()

    if failed_count == 0 and corrupted_remaining < 500:
        print("\n🎉 SUCCESS: Timestamps restored successfully!")
    else:
        print(f"\n⚠️  WARNING: Some issues occurred during restoration")


if __name__ == "__main__":
    dry_run = '--apply' not in sys.argv

    db_path = config.SQLITE_VEC_PATH
    mapping_file = Path(__file__).parent.parent.parent / "clean_timestamp_mapping.json"

    if not mapping_file.exists():
        print(f"❌ ERROR: Mapping file not found: {mapping_file}")
        print("Run Phase 1 first to extract the clean timestamp mapping")
        sys.exit(1)

    try:
        restore_from_json(str(db_path), str(mapping_file), dry_run=dry_run)
    except KeyboardInterrupt:
        print("\n\nRestoration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Restoration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
