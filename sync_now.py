#!/usr/bin/env python3
"""
Manual sync utility for Hybrid Storage Backend.
Triggers an immediate sync from SQLite-vec to Cloudflare.

Usage:
    python sync_now.py [--db-path PATH]

Environment Variables:
    MCP_MEMORY_SQLITE_PATH: Override default database path
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path

# Import from installed package (assumes package is installed in editable mode)
try:
    from dotenv import load_dotenv
    from mcp_memory_service.storage.factory import create_storage_instance
    from mcp_memory_service.storage.hybrid import HybridMemoryStorage
    from mcp_memory_service.config import SQLITE_VEC_PATH
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure the package is installed: pip install -e .")
    sys.exit(1)


async def main(db_path: str | None = None):
    """
    Run immediate sync.

    Args:
        db_path: Optional path to SQLite database. If not provided,
                uses MCP_MEMORY_SQLITE_PATH env var or default config.
    """
    # Load environment variables
    load_dotenv()

    print("🔄 Starting manual sync...")

    # Determine database path
    if db_path:
        sqlite_path = Path(db_path)
    elif os.getenv('MCP_MEMORY_SQLITE_PATH'):
        sqlite_path = Path(os.getenv('MCP_MEMORY_SQLITE_PATH'))
    else:
        sqlite_path = Path(SQLITE_VEC_PATH)

    if not sqlite_path.exists():
        print(f"❌ Database not found: {sqlite_path}")
        return 1

    print(f"📁 Using database: {sqlite_path}")

    # Create storage instance
    try:
        storage = await create_storage_instance(str(sqlite_path))
    except Exception as e:
        print(f"❌ Failed to create storage instance: {e}")
        return 1

    # Type-safe check for hybrid storage
    if not isinstance(storage, HybridMemoryStorage):
        print("❌ Not a hybrid backend - sync not available")
        print(f"   Found: {storage.__class__.__name__}")
        return 1

    # Get sync status before
    try:
        status_before = storage.sync_service.get_status()
        print(f"📊 Before sync:")
        print(f"   Queue size: {status_before['queue_size']}")
        print(f"   Cloudflare available: {status_before['cloudflare_available']}")
    except Exception as e:
        print(f"⚠️  Could not get sync status: {e}")

    # Trigger immediate sync using public method
    print("\n⏳ Triggering sync...")
    try:
        # Check if there's a public sync method, otherwise use the internal one
        if hasattr(storage.sync_service, 'sync_now'):
            await storage.sync_service.sync_now()
        elif hasattr(storage.sync_service, '_sync_batch'):
            # Fallback to internal method if public method doesn't exist yet
            await storage.sync_service._sync_batch()
        else:
            print("❌ No sync method available on sync service")
            return 1
        print("✅ Sync completed successfully!")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Get sync status after
    try:
        status_after = storage.sync_service.get_status()
        print(f"\n📊 After sync:")
        print(f"   Operations processed: {status_after['stats']['operations_processed']}")
        print(f"   Last sync duration: {status_after['stats']['last_sync_duration']:.2f}s")
        print(f"   Queue size: {status_after['queue_size']}")
    except Exception as e:
        print(f"⚠️  Could not get final sync status: {e}")

    return 0


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Manual sync utility for Hybrid Storage Backend"
    )
    parser.add_argument(
        '--db-path',
        type=str,
        help='Path to SQLite database (default: from config or env)'
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = asyncio.run(main(db_path=args.db_path))
    sys.exit(exit_code)
