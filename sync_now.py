#!/usr/bin/env python3
"""
Manual sync utility for Hybrid Storage Backend.
Triggers an immediate sync from SQLite-vec to Cloudflare.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
load_dotenv()

from mcp_memory_service.storage.factory import create_storage_instance

async def main():
    """Run immediate sync."""
    print("🔄 Starting manual sync...")

    # Create storage instance
    sqlite_path = Path.home() / ".local" / "share" / "mcp-memory" / "sqlite_vec.db"
    storage = await create_storage_instance(str(sqlite_path))

    if not hasattr(storage, 'sync_service'):
        print("❌ Not a hybrid backend - sync not available")
        return 1

    # Get sync status before
    status_before = storage.sync_service.get_status()
    print(f"📊 Before sync:")
    print(f"   Queue size: {status_before['queue_size']}")
    print(f"   Cloudflare available: {status_before['cloudflare_available']}")

    # Trigger immediate sync
    print("\n⏳ Triggering sync...")
    try:
        await storage.sync_service._sync_batch()
        print("✅ Sync completed successfully!")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        return 1

    # Get sync status after
    status_after = storage.sync_service.get_status()
    print(f"\n📊 After sync:")
    print(f"   Operations processed: {status_after['stats']['operations_processed']}")
    print(f"   Last sync duration: {status_after['stats']['last_sync_duration']:.2f}s")
    print(f"   Queue size: {status_after['queue_size']}")

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
