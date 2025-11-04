#!/usr/bin/env python3
"""Quick script to check memory types in local database."""
import sqlite3
from pathlib import Path

# Windows database path
db_path = Path.home() / "AppData/Local/mcp-memory/sqlite_vec.db"

if not db_path.exists():
    print(f"❌ Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get memory type distribution
cursor.execute("""
    SELECT memory_type, COUNT(*) as count
    FROM memories
    GROUP BY memory_type
    ORDER BY count DESC
""")

results = cursor.fetchall()
total = sum(count for _, count in results)

print(f"\nMemory Type Distribution")
print("=" * 60)
print(f"Total memories: {total:,}")
print(f"Unique types: {len(results)}\n")

print(f"{'Memory Type':<40} {'Count':>8} {'%':>6}")
print("-" * 60)

for memory_type, count in results[:30]:  # Show top 30
    pct = (count / total) * 100 if total > 0 else 0
    type_display = memory_type if memory_type else "(empty/NULL)"
    print(f"{type_display:<40} {count:>8,} {pct:>5.1f}%")

if len(results) > 30:
    remaining = len(results) - 30
    remaining_count = sum(count for _, count in results[30:])
    print(f"\n... and {remaining} more types ({remaining_count:,} memories)")

conn.close()
