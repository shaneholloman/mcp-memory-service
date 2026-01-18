#!/usr/bin/env python3
"""
Migration script to add relationship_type column to memory_graph table.

This migration is required for v9.0.0+ Knowledge Graph features.
It adds the relationship_type column to store typed relationships between memories.

Usage:
    python scripts/migration/add_relationship_type_column.py

Or with custom database path:
    python scripts/migration/add_relationship_type_column.py --db-path /path/to/sqlite_vec.db
"""

import sqlite3
import argparse
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from mcp_memory_service.config import SQLITE_VEC_PATH


def add_relationship_type_column(db_path: str):
    """Add relationship_type column to memory_graph table."""

    print(f"Connecting to database: {db_path}")

    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(memory_graph)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'relationship_type' in columns:
            print("✅ Column 'relationship_type' already exists. No migration needed.")
            return True

        print("📋 Current schema:")
        for col in columns:
            print(f"   - {col}")

        # Count existing relationships
        cursor.execute("SELECT COUNT(*) FROM memory_graph")
        total_relationships = cursor.fetchone()[0]
        print(f"\n📊 Found {total_relationships} existing relationships")

        # Add the column (defaults to NULL, which renders as 'related' in frontend)
        print("\n🔧 Adding 'relationship_type' column...")
        cursor.execute("""
            ALTER TABLE memory_graph
            ADD COLUMN relationship_type TEXT DEFAULT 'related'
        """)

        conn.commit()

        # Verify the column was added
        cursor.execute("PRAGMA table_info(memory_graph)")
        new_columns = [row[1] for row in cursor.fetchall()]

        if 'relationship_type' in new_columns:
            print("✅ Successfully added 'relationship_type' column!")
            print("\n📋 Updated schema:")
            for col in new_columns:
                print(f"   - {col}")

            print(f"\n✨ Migration complete! All {total_relationships} existing relationships")
            print("   have been set to 'related' (the default type).")
            print("\n💡 New relationships created via MCP tools will use typed relationships")
            print("   (causes, fixes, contradicts, supports, follows, related)")
            return True
        else:
            print("❌ Failed to add column")
            return False

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Add relationship_type column to memory_graph table (v9.0.0 migration)'
    )
    parser.add_argument(
        '--db-path',
        default=SQLITE_VEC_PATH,
        help=f'Path to SQLite database (default: {SQLITE_VEC_PATH})'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Knowledge Graph Schema Migration (v9.0.0)")
    print("=" * 70)
    print()

    success = add_relationship_type_column(args.db_path)

    print()
    print("=" * 70)

    if success:
        print("✅ Migration completed successfully!")
        print("\n🚀 Next steps:")
        print("   1. Restart the HTTP server: python scripts/server/run_http_server.py")
        print("   2. Open dashboard: http://localhost:8000")
        print("   3. Navigate to Analytics → Knowledge Graph")
        print("   4. You should now see your relationship data visualized!")
        sys.exit(0)
    else:
        print("❌ Migration failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
