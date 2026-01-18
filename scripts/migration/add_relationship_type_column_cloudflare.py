#!/usr/bin/env python3
"""
Migration script to add relationship_type column to Cloudflare D1 memory_graph table.

This migration is required for v9.0.0+ Knowledge Graph features in Cloudflare/Hybrid backends.
It adds the relationship_type column to store typed relationships between memories.

Usage:
    python scripts/migration/add_relationship_type_column_cloudflare.py

Prerequisites:
    - CLOUDFLARE_API_TOKEN environment variable must be set
    - CLOUDFLARE_ACCOUNT_ID environment variable must be set
    - CLOUDFLARE_D1_DATABASE_ID environment variable must be set

Or provide via command line:
    python scripts/migration/add_relationship_type_column_cloudflare.py \
        --api-token YOUR_TOKEN \
        --account-id YOUR_ACCOUNT \
        --database-id YOUR_DB_ID
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from mcp_memory_service.storage.cloudflare import CloudflareStorage
from mcp_memory_service.config import (
    CLOUDFLARE_API_TOKEN,
    CLOUDFLARE_ACCOUNT_ID,
    CLOUDFLARE_D1_DATABASE_ID
)


async def check_column_exists(storage: CloudflareStorage) -> bool:
    """Check if relationship_type column already exists."""
    try:
        # Use PRAGMA table_info to check schema
        check_sql = "PRAGMA table_info(memory_graph)"
        payload = {"sql": check_sql}
        response = await storage._retry_request("POST", f"{storage.d1_url}/query", json=payload)
        result = response.json()

        if result.get("success") and result.get("result", [{}])[0].get("results"):
            columns = {row["name"] for row in result["result"][0]["results"] if "name" in row}
            return "relationship_type" in columns
        return False
    except Exception:
        return False


async def count_relationships(storage: CloudflareStorage) -> int:
    """Count total relationships in memory_graph."""
    try:
        count_sql = "SELECT COUNT(*) as count FROM memory_graph"
        payload = {"sql": count_sql}
        response = await storage._retry_request("POST", f"{storage.d1_url}/query", json=payload)
        result = response.json()

        if result.get("success") and result.get("result", [{}])[0].get("results"):
            return result["result"][0]["results"][0].get("count", 0)
        return 0
    except Exception as e:
        print(f"⚠️  Warning: Could not count relationships: {e}")
        return 0


async def add_relationship_type_column_cloudflare(
    api_token: str,
    account_id: str,
    database_id: str
):
    """Add relationship_type column to Cloudflare D1 memory_graph table."""

    print("Connecting to Cloudflare D1...")

    try:
        storage = CloudflareStorage(
            api_token=api_token,
            account_id=account_id,
            d1_database_id=database_id,
            vectorize_index="mcp-memory-index"  # Not needed for migration
        )

        # Initialize storage
        await storage.initialize()

        # Check if column already exists
        print("Checking if column already exists...")
        if await check_column_exists(storage):
            print("✅ Column 'relationship_type' already exists. No migration needed.")
            return True

        # Count existing relationships
        total_relationships = await count_relationships(storage)
        print(f"\n📊 Found {total_relationships} existing relationships")

        # Add the column to D1 database
        print("\n🔧 Adding 'relationship_type' column to Cloudflare D1...")

        # D1 SQL: ALTER TABLE ADD COLUMN with DEFAULT value
        alter_query = """
            ALTER TABLE memory_graph
            ADD COLUMN relationship_type TEXT DEFAULT 'related'
        """

        payload = {"sql": alter_query}
        response = await storage._retry_request("POST", f"{storage.d1_url}/query", json=payload)
        result = response.json()

        if not result.get("success"):
            print(f"❌ Failed to add column: {result}")
            return False

        # Verify the column was added
        print("🔍 Verifying column was added...")
        if await check_column_exists(storage):
            print("✅ Successfully added 'relationship_type' column to Cloudflare D1!")
            print(f"\n✨ Migration complete! All {total_relationships} existing relationships")
            print("   have been set to 'related' (the default type).")
            print("\n💡 New relationships created via MCP tools will use typed relationships")
            print("   (causes, fixes, contradicts, supports, follows, related)")
            return True
        else:
            print("❌ Failed to verify column addition")
            return False

    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Add relationship_type column to Cloudflare D1 memory_graph table (v9.0.0 migration)'
    )
    parser.add_argument(
        '--api-token',
        default=CLOUDFLARE_API_TOKEN,
        help='Cloudflare API token'
    )
    parser.add_argument(
        '--account-id',
        default=CLOUDFLARE_ACCOUNT_ID,
        help='Cloudflare account ID'
    )
    parser.add_argument(
        '--database-id',
        default=CLOUDFLARE_D1_DATABASE_ID,
        help='Cloudflare D1 database ID'
    )

    args = parser.parse_args()

    # Validate credentials
    if not args.api_token or not args.account_id or not args.database_id:
        print("❌ Error: Missing Cloudflare credentials!")
        print("\nPlease provide:")
        print("  1. Set environment variables: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_D1_DATABASE_ID")
        print("  2. Or use command line: --api-token TOKEN --account-id ACCOUNT --database-id DB_ID")
        sys.exit(1)

    print("=" * 70)
    print("Cloudflare D1 Knowledge Graph Schema Migration (v9.0.0)")
    print("=" * 70)
    print(f"\nAccount ID: {args.account_id}")
    print(f"Database ID: {args.database_id}")
    print()

    success = asyncio.run(add_relationship_type_column_cloudflare(
        args.api_token,
        args.account_id,
        args.database_id
    ))

    print()
    print("=" * 70)

    if success:
        print("✅ Cloudflare D1 migration completed successfully!")
        print("\n🚀 Next steps:")
        print("   1. Restart the HTTP server: python scripts/server/run_http_server.py")
        print("   2. Open dashboard: http://localhost:8000")
        print("   3. Navigate to Analytics → Knowledge Graph")
        print("   4. Your Cloudflare data is now ready for visualization!")
        print("\n💡 Note: If using hybrid backend, both SQLite and Cloudflare")
        print("   migrations are required. Run both scripts.")
        sys.exit(0)
    else:
        print("❌ Cloudflare D1 migration failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
