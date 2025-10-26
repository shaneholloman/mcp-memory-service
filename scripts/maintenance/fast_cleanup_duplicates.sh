#!/bin/bash
# Fast duplicate cleanup using direct SQL
set -e

DB_PATH="$HOME/.local/share/mcp-memory/sqlite_vec.db"

echo "🛑 Stopping HTTP server..."
systemctl --user stop mcp-memory-http.service 2>/dev/null || true
sleep 2

echo "📊 Analyzing duplicates..."

# Create Python script to find and delete duplicates
python3 << 'PYTHON_SCRIPT'
import sqlite3
from pathlib import Path
from collections import defaultdict
import hashlib
import re

DB_PATH = Path.home() / ".local/share/mcp-memory/sqlite_vec.db"

def normalize_content(content):
    """Normalize content by removing timestamps."""
    normalized = content
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z', 'TIMESTAMP', normalized)
    normalized = re.sub(r'\*\*Date\*\*: \d{2,4}[./]\d{2}[./]\d{2,4}', '**Date**: DATE', normalized)
    normalized = re.sub(r'Timestamp: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', 'Timestamp: TIMESTAMP', normalized)
    return normalized.strip()

def get_normalized_hash(content):
    """Create a hash of normalized content."""
    normalized = normalize_content(content)
    return hashlib.md5(normalized.encode()).hexdigest()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Analyzing memories...")
cursor.execute("SELECT id, content_hash, content, created_at FROM memories ORDER BY created_at DESC")
memories = cursor.fetchall()

print(f"Total memories: {len(memories)}")

# Group by normalized content
content_groups = defaultdict(list)
for mem_id, mem_hash, mem_content, created_at in memories:
    norm_hash = get_normalized_hash(mem_content)
    content_groups[norm_hash].append({
        'id': mem_id,
        'hash': mem_hash,
        'created_at': created_at
    })

# Find duplicates
duplicates = {k: v for k, v in content_groups.items() if len(v) > 1}

if not duplicates:
    print("✅ No duplicates found!")
    conn.close()
    exit(0)

print(f"Found {len(duplicates)} duplicate groups")

# Collect IDs to delete (keep newest, delete older)
ids_to_delete = []
for group in duplicates.values():
    for memory in group[1:]:  # Keep first (newest), delete rest
        ids_to_delete.append(memory['id'])

print(f"Deleting {len(ids_to_delete)} duplicate memories...")

# Delete from memories table
placeholders = ','.join('?' * len(ids_to_delete))
cursor.execute(f"DELETE FROM memories WHERE id IN ({placeholders})", ids_to_delete)

# Note: Can't delete from virtual table without vec0 extension
# Orphaned embeddings will be cleaned up on next regeneration

conn.commit()
conn.close()

print(f"✅ Deleted {len(ids_to_delete)} duplicates")

PYTHON_SCRIPT

echo "🚀 Restarting HTTP server..."
systemctl --user start mcp-memory-http.service

echo "✅ Cleanup complete!"
