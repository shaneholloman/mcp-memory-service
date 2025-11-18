#!/usr/bin/env python3
"""
Timestamp Recovery Script - Recover corrupted timestamps from Cloudflare

This script helps recover from the timestamp regression bug (v8.25.0-v8.27.0)
where created_at timestamps were reset during metadata sync operations.

If you use the hybrid backend and Cloudflare has the correct timestamps,
this script will restore them to your local SQLite database.

Usage:
    python scripts/maintenance/recover_timestamps_from_cloudflare.py --dry-run
    python scripts/maintenance/recover_timestamps_from_cloudflare.py  # Apply fixes
"""

import asyncio
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_memory_service.storage.factory import create_storage_instance
from mcp_memory_service.storage.hybrid import HybridMemoryStorage
from mcp_memory_service.config import get_config


class TimestampRecovery:
    """Recover corrupted timestamps from Cloudflare."""

    def __init__(self, hybrid_storage: HybridMemoryStorage, dry_run: bool = True):
        self.hybrid = hybrid_storage
        self.primary = hybrid_storage.primary  # SQLite-vec
        self.secondary = hybrid_storage.secondary  # Cloudflare
        self.dry_run = dry_run

        self.stats = {
            'total_checked': 0,
            'mismatches_found': 0,
            'recovered': 0,
            'errors': 0,
            'skipped': 0
        }

    async def recover_all_timestamps(self) -> Tuple[bool, dict]:
        """
        Recover timestamps for all memories by comparing SQLite vs Cloudflare.

        Returns:
            Tuple of (success, stats_dict)
        """
        print("="*70)
        print("⏰ TIMESTAMP RECOVERY FROM CLOUDFLARE")
        print("="*70)
        print(f"Mode: {'DRY RUN (no changes)' if self.dry_run else 'LIVE (will apply fixes)'}")
        print()

        try:
            # Get all memories from both backends
            print("1️⃣ Fetching memories from local SQLite...")
            local_memories = await self._get_all_local_memories()
            print(f"   Found {len(local_memories)} local memories")

            print("\n2️⃣ Fetching memories from Cloudflare...")
            cf_memories = await self._get_all_cloudflare_memories()
            print(f"   Found {len(cf_memories)} Cloudflare memories")

            # Build Cloudflare memory lookup
            cf_lookup = {m.content_hash: m for m in cf_memories}

            print("\n3️⃣ Comparing timestamps...")
            mismatches = []

            for local_memory in local_memories:
                self.stats['total_checked'] += 1
                content_hash = local_memory.content_hash

                cf_memory = cf_lookup.get(content_hash)
                if not cf_memory:
                    self.stats['skipped'] += 1
                    continue

                # Compare timestamps (allow 1 second tolerance)
                if abs(local_memory.created_at - cf_memory.created_at) > 1.0:
                    mismatches.append((local_memory, cf_memory))
                    self.stats['mismatches_found'] += 1

            if not mismatches:
                print("   ✅ No timestamp mismatches found!")
                return True, self.stats

            print(f"   ⚠️  Found {len(mismatches)} timestamp mismatches")

            # Analyze and fix mismatches
            print("\n4️⃣ Analyzing and fixing mismatches...")
            await self._fix_mismatches(mismatches)

            # Print summary
            print("\n" + "="*70)
            print("📊 RECOVERY SUMMARY")
            print("="*70)
            print(f"Total checked:      {self.stats['total_checked']}")
            print(f"Mismatches found:   {self.stats['mismatches_found']}")
            print(f"Recovered:          {self.stats['recovered']}")
            print(f"Errors:             {self.stats['errors']}")
            print(f"Skipped:            {self.stats['skipped']}")

            if self.dry_run:
                print("\n💡 This was a DRY RUN. Run without --dry-run to apply fixes.")
            else:
                print("\n✅ Recovery complete! Timestamps have been restored.")

            return self.stats['errors'] == 0, self.stats

        except Exception as e:
            print(f"\n❌ Recovery failed: {e}")
            import traceback
            traceback.print_exc()
            return False, self.stats

    async def _get_all_local_memories(self) -> List:
        """Get all memories from local SQLite."""
        if not hasattr(self.primary, 'conn'):
            raise ValueError("Primary storage must be SQLite-vec")

        cursor = self.primary.conn.execute('''
            SELECT content_hash, created_at, created_at_iso, updated_at, updated_at_iso
            FROM memories
            ORDER BY created_at
        ''')

        class LocalMemory:
            def __init__(self, content_hash, created_at, created_at_iso, updated_at, updated_at_iso):
                self.content_hash = content_hash
                self.created_at = created_at
                self.created_at_iso = created_at_iso
                self.updated_at = updated_at
                self.updated_at_iso = updated_at_iso

        memories = []
        for row in cursor.fetchall():
            memories.append(LocalMemory(*row))

        return memories

    async def _get_all_cloudflare_memories(self) -> List:
        """Get all memories from Cloudflare."""
        # Use search_by_tag with empty tag list to get all
        # (Cloudflare backend may not have a get_all method)
        try:
            # Try to get all via D1 query
            if hasattr(self.secondary, '_retry_request'):
                sql = '''
                    SELECT content_hash, created_at, created_at_iso,
                           updated_at, updated_at_iso
                    FROM memories
                    ORDER BY created_at
                '''
                payload = {"sql": sql, "params": []}
                response = await self.secondary._retry_request(
                    "POST",
                    f"{self.secondary.d1_url}/query",
                    json=payload
                )
                result = response.json()

                if result.get("success") and result.get("result", [{}])[0].get("results"):
                    class CFMemory:
                        def __init__(self, content_hash, created_at, created_at_iso, updated_at, updated_at_iso):
                            self.content_hash = content_hash
                            self.created_at = created_at
                            self.created_at_iso = created_at_iso
                            self.updated_at = updated_at
                            self.updated_at_iso = updated_at_iso

                    memories = []
                    for row in result["result"][0]["results"]:
                        memories.append(CFMemory(
                            row["content_hash"],
                            row["created_at"],
                            row["created_at_iso"],
                            row["updated_at"],
                            row["updated_at_iso"]
                        ))

                    return memories

        except Exception as e:
            print(f"   ⚠️  Could not fetch Cloudflare memories: {e}")

        return []

    async def _fix_mismatches(self, mismatches: List[Tuple]) -> None:
        """Fix timestamp mismatches by updating local from Cloudflare."""
        for i, (local, cf) in enumerate(mismatches, 1):
            try:
                # Determine which is correct based on logic:
                # - Cloudflare should have the original created_at
                # - If local created_at is very recent but Cloudflare is old,
                #   it's likely the bug (reset to current time)

                local_age = time.time() - local.created_at
                cf_age = time.time() - cf.created_at

                # If local is < 24h old but CF is > 7 days old, likely corrupted
                is_likely_corrupted = local_age < 86400 and cf_age > 604800

                if is_likely_corrupted or cf.created_at < local.created_at:
                    # Use Cloudflare timestamp (it's older/more likely correct)
                    if i <= 5:  # Show first 5
                        print(f"\n   {i}. {local.content_hash[:8]}:")
                        print(f"      Local:      {local.created_at_iso} ({local_age/86400:.1f} days ago)")
                        print(f"      Cloudflare: {cf.created_at_iso} ({cf_age/86400:.1f} days ago)")
                        print(f"      → Restoring from Cloudflare")

                    if not self.dry_run:
                        # Update local SQLite with Cloudflare timestamps
                        success, _ = await self.primary.update_memory_metadata(
                            local.content_hash,
                            {
                                'created_at': cf.created_at,
                                'created_at_iso': cf.created_at_iso,
                                'updated_at': cf.updated_at,
                                'updated_at_iso': cf.updated_at_iso,
                            },
                            preserve_timestamps=False  # Use provided timestamps
                        )

                        if success:
                            self.stats['recovered'] += 1
                        else:
                            self.stats['errors'] += 1
                            print(f"      ❌ Failed to update")
                    else:
                        self.stats['recovered'] += 1  # Would recover

                else:
                    # Local is older, keep it
                    if i <= 5:
                        print(f"\n   {i}. {local.content_hash[:8]}: Local older, keeping local")
                    self.stats['skipped'] += 1

            except Exception as e:
                print(f"      ❌ Error: {e}")
                self.stats['errors'] += 1

        if len(mismatches) > 5:
            print(f"\n   ... and {len(mismatches) - 5} more")


async def main():
    """Main recovery function."""
    parser = argparse.ArgumentParser(
        description="Recover corrupted timestamps from Cloudflare backup"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them (default: True unless explicitly disabled)"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply fixes (overrides dry-run)"
    )

    args = parser.parse_args()

    # Default to dry-run unless --apply is specified
    dry_run = not args.apply

    try:
        # Initialize hybrid storage
        config = get_config()

        if config.storage_backend != "hybrid":
            print("❌ This script requires hybrid backend")
            print(f"   Current backend: {config.storage_backend}")
            print("\n   To use hybrid backend, set in .env:")
            print("   MCP_MEMORY_STORAGE_BACKEND=hybrid")
            sys.exit(1)

        storage = await create_storage_instance(config.sqlite_db_path)

        if not isinstance(storage, HybridMemoryStorage):
            print("❌ Storage is not hybrid backend")
            sys.exit(1)

        # Run recovery
        recovery = TimestampRecovery(storage, dry_run=dry_run)
        success, stats = await recovery.recover_all_timestamps()

        # Close storage
        if hasattr(storage, 'close'):
            storage.close()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Recovery failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
