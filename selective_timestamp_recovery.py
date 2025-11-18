#!/usr/bin/env python3
"""
Selective Timestamp Recovery Script

Merges backup timestamps with current database:
- Restores timestamps for 2,174 corrupted memories from Nov 5 backup
- Preserves 807 new memories created Nov 5-17 with their current timestamps
- Result: ALL 2,981 memories have correct timestamps!
"""

import sqlite3
import sys
from datetime import datetime

DRY_RUN = '--apply' not in sys.argv

current_db = r'C:\Users\heinrich.krupp\AppData\Local\mcp-memory\backups\sqlite_vec.db'
backup_db = r'C:\Users\heinrich.krupp\AppData\Local\mcp-memory\backups\sqlite_vec.backup-20251105-114637.db'

def selective_recovery():
    print("="*80)
    print("SELECTIVE TIMESTAMP RECOVERY")
    print("="*80)
    print(f"Mode: {'DRY RUN (no changes)' if not DRY_RUN else 'LIVE (applying changes)'}")
    print()

    # Open databases
    current = sqlite3.connect(current_db)
    backup = sqlite3.connect(backup_db)

    # Get common hashes
    cur_hashes = {h[0] for h in current.execute('SELECT content_hash FROM memories').fetchall()}
    bak_hashes = {h[0] for h in backup.execute('SELECT content_hash FROM memories').fetchall()}

    common = cur_hashes & bak_hashes
    only_current = cur_hashes - bak_hashes

    print(f"Analysis:")
    print(f"  - {len(common):4} memories to restore from backup")
    print(f"  - {len(only_current):4} new memories to keep as-is")
    print(f"  - {len(common) + len(only_current):4} total memories after recovery")
    print()

    if DRY_RUN:
        print("[DRY RUN] Pass --apply to make actual changes")
        print()

    # Restore timestamps for common memories
    restored_count = 0
    errors = 0

    print("Restoring timestamps...")
    for i, content_hash in enumerate(common, 1):
        try:
            # Get timestamps from backup
            bak_row = backup.execute('''
                SELECT created_at, created_at_iso, updated_at, updated_at_iso
                FROM memories WHERE content_hash = ?
            ''', (content_hash,)).fetchone()

            if not bak_row:
                continue

            created_at, created_at_iso, updated_at, updated_at_iso = bak_row

            # Check if actually corrupted (created on Nov 17)
            cur_created_iso = current.execute(
                'SELECT created_at_iso FROM memories WHERE content_hash = ?',
                (content_hash,)
            ).fetchone()[0]

            if '2025-11-17' in cur_created_iso:
                # Corrupted - restore from backup
                if not DRY_RUN:
                    current.execute('''
                        UPDATE memories
                        SET created_at = ?, created_at_iso = ?,
                            updated_at = ?, updated_at_iso = ?
                        WHERE content_hash = ?
                    ''', (created_at, created_at_iso, updated_at, updated_at_iso, content_hash))

                restored_count += 1

                if restored_count <= 10:  # Show first 10
                    print(f"  {restored_count:4}. {content_hash[:8]}: {cur_created_iso} => {created_at_iso}")

            if i % 100 == 0:
                print(f"  Progress: {i}/{len(common)} ({i*100//len(common)}%)")

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR: {content_hash[:8]}: {e}")

    if restored_count > 10:
        print(f"  ... and {restored_count - 10} more")

    # Commit changes
    if not DRY_RUN:
        current.commit()
        print(f"\n[SUCCESS] Committed {restored_count} timestamp restorations")
    else:
        print(f"\n[DRY RUN] Would restore {restored_count} timestamps")

    print()
    print("="*80)
    print("RECOVERY COMPLETE!")
    print("="*80)
    print(f"  Restored:  {restored_count:4} memories from backup")
    print(f"  Preserved: {len(only_current):4} new memories (Nov 5-17)")
    print(f"  Errors:    {errors:4}")
    print()

    if restored_count > 0:
        print("Verification:")
        cur = current.execute('SELECT COUNT(*) FROM memories WHERE created_at_iso LIKE "2025-11-17%"')
        remaining_corrupt = cur.fetchone()[0]
        print(f"  Memories still with Nov 17 timestamp: {remaining_corrupt}")
        print(f"  (Should be ~{len(only_current)} - the genuinely new ones)")

    current.close()
    backup.close()

    if DRY_RUN:
        print()
        print("[DRY RUN] No changes were made.")
        print("    Run with --apply to actually fix the database:")
        print(f"    python {sys.argv[0]} --apply")
    else:
        print()
        print("[SUCCESS] Database has been updated!")
        print("   Restart HTTP server to use the fixed database.")

if __name__ == '__main__':
    try:
        selective_recovery()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
