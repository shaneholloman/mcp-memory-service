# Database Transfer and Migration Issues

This guide covers common issues encountered when transferring or migrating the MCP Memory Service database across machines or platforms.

## SQLite-vec Database Corruption During Transfer

### Symptom

After transferring `sqlite_vec.db` via SCP or rsync, the database appears corrupted:

```
Failed to initialize SQLite-vec storage: database disk image is malformed
```

Server logs show:
```
Failed to apply pragma journal_mode: database disk image is malformed
Failed to apply pragma synchronous: database disk image is malformed
```

### Verification

```bash
# On source machine (works)
sqlite3 /path/to/sqlite_vec.db "PRAGMA integrity_check;"
# Returns: ok

# After SCP transfer to destination
sqlite3 /path/to/sqlite_vec.db "PRAGMA integrity_check;"
# Returns: Error: database disk image is malformed (11)
```

### Root Cause

The sqlite-vec extension uses binary format that can be corrupted during network transfer via SCP/rsync. This is particularly common when transferring between different platforms (e.g., Linux → macOS).

### Solution: Use tar+gzip for Transfer

**Step 1: Create archive on source machine**
```bash
# Include all DB files (main DB + WAL + SHM)
cd ~/.local/share/mcp-memory
tar czf /tmp/sqlite_vec.tar.gz sqlite_vec.db*
```

**Step 2: Transfer archive**
```bash
# From destination machine
scp user@source-host:/tmp/sqlite_vec.tar.gz ~/Downloads/
```

**Step 3: Extract on destination**
```bash
cd ~/Downloads
tar xzf sqlite_vec.tar.gz

# Verify integrity
sqlite3 sqlite_vec.db "PRAGMA integrity_check;"
# Should return: ok
```

**Step 4: Move to target location**
```bash
# macOS
cp sqlite_vec.db* ~/Library/Application\ Support/mcp-memory/

# Linux
cp sqlite_vec.db* ~/.local/share/mcp-memory/
```

### Why tar+gzip Works

- tar preserves exact binary format without modification
- gzip compression doesn't interfere with sqlite-vec extension data
- Entire file is treated as opaque binary blob

### Failed Approaches

❌ **Direct SCP**: Always corrupts sqlite-vec extension data
❌ **sqlite3 .dump | pipe**: Doesn't handle vector extension tables
❌ **Multiple SCP retries**: Same corruption pattern

## Web Dashboard Export Format Incompatibility

### Symptom

After exporting memories from the Web Dashboard (http://127.0.0.1:8000/) and trying to import with `scripts/sync/import_memories.py`:

```
ERROR - Invalid export format in export.json
Expected either CLI format (export_metadata) or Web Dashboard format (export_date)
```

### Root Cause

Two different export formats exist:

**Web Dashboard Export** (as of v8.67.0):
```json
{
  "export_date": "2026-01-03T05:31:30.396Z",
  "total_memories": 4188,
  "exported_memories": 4188,
  "memories": [...]
}
```

**CLI Export** (sync/exporter.py):
```json
{
  "export_metadata": {
    "source_machine": "hostname",
    "export_timestamp": "2026-01-03T05:31:30.396Z",
    "total_memories": 4188,
    ...
  },
  "memories": [...]
}
```

### Solution (v8.68.0+)

The import script now auto-detects both formats. If you're on an older version, manually convert:

```python
import json

# Read Web Dashboard export
with open('web-export.json', 'r') as f:
    data = json.load(f)

# Add CLI format wrapper
data['export_metadata'] = {
    'export_timestamp': data.get('export_date', ''),
    'total_memories': data.get('total_memories', 0),
    'source_machine': 'web-dashboard-export',
    'exporter_version': 'web-dashboard'
}

# Save converted file
with open('converted-export.json', 'w') as f:
    json.dump(data, f, indent=2)
```

Then import as normal:
```bash
python scripts/sync/import_memories.py converted-export.json
```

## Schema Migration Not Applied

### Symptom

Dashboard shows "0 memories" despite database containing thousands of records:

```bash
sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db "SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL;"
# Returns: 4188

# But tags column is empty
sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db "SELECT tags FROM memories LIMIT 1;"
# Returns: []
```

Server logs show:
```
Error getting all memories: no such column: m.tags
Database error getting stats: no such column: tags
```

### Root Cause

Database was created before schema migration (v8.64.0+) that added the `tags` column. The code expects the new schema, but the database was never migrated.

Tags are still stored in the old format:
```sql
SELECT metadata FROM memories LIMIT 1;
-- Returns: {"tags": "tag1,tag2,tag3", ...}
```

### Diagnosis

Check if migration is needed:

```bash
sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db "PRAGMA table_info(memories);" | grep tags
```

If you see:
- Column exists but empty → Migration needed
- No tags column → Schema needs update

### Solution: Manual Migration

**⚠️ IMPORTANT: Backup first!**

```bash
# Create backup
cp ~/.local/share/mcp-memory/sqlite_vec.db ~/.local/share/mcp-memory/sqlite_vec.db.backup-$(date +%Y%m%d)
```

**Add missing columns (if needed):**
```sql
sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db << 'EOF'
-- Add tags column if missing
ALTER TABLE memories ADD COLUMN tags TEXT DEFAULT '[]';

-- Add updated_at column if missing
ALTER TABLE memories ADD COLUMN updated_at REAL;

-- Set updated_at = created_at for existing records
UPDATE memories SET updated_at = created_at WHERE updated_at IS NULL;

-- Verify
PRAGMA table_info(memories);
EOF
```

**Migrate tags from metadata:**
```sql
sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db << 'EOF'
-- Copy tags from metadata JSON to tags column
UPDATE memories
SET tags = json_extract(metadata, '$.tags')
WHERE json_extract(metadata, '$.tags') IS NOT NULL;

-- Verify migration
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN tags != '[]' THEN 1 END) as with_tags
FROM memories;
EOF
```

**Restart server** to apply changes.

### Prevention

The service should automatically run migrations on startup (v8.64.0+). If you encounter this:

1. Check you're running the latest version
2. Review server startup logs for migration messages
3. Report as bug if migrations aren't running

## Backup Best Practices

Based on lessons learned from transfer corruption issues:

### ✅ Recommended Backup Method

```bash
# Create timestamped backup with tar+gzip
BACKUP_DIR=~/.local/share/mcp-memory/backups/manual_$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

cd ~/.local/share/mcp-memory
tar czf "$BACKUP_DIR/sqlite_vec.tar.gz" sqlite_vec.db*

# Verify backup integrity
cd "$BACKUP_DIR"
tar xzf sqlite_vec.tar.gz
sqlite3 sqlite_vec.db "PRAGMA integrity_check; SELECT COUNT(*) FROM memories;"
```

### Backup Verification Checklist

After creating any backup:

```bash
# 1. Integrity check
sqlite3 /path/to/backup/sqlite_vec.db "PRAGMA integrity_check;"
# Should return: ok

# 2. Record count
sqlite3 /path/to/backup/sqlite_vec.db "SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL;"
# Should match expected count

# 3. Schema verification
sqlite3 /path/to/backup/sqlite_vec.db "PRAGMA table_info(memories);" | grep -E "tags|updated_at"
# Should show both columns
```

### Cross-Platform Transfer

When moving database between different systems:

1. ✅ Always use **tar+gzip**
2. ✅ Verify integrity on source **before** transfer
3. ✅ Verify integrity on destination **after** extraction
4. ✅ Test with small query before full deployment
5. ❌ Never use direct SCP/rsync for sqlite_vec.db

## Related Documentation

- [Hooks Quick Reference](./hooks-quick-reference.md) - Hook configuration troubleshooting
- [Database Restoration Guide](../guides/database-restoration.md) - Complete restoration procedures
- [CLAUDE.md](../../CLAUDE.md) - Essential commands and configuration

## Getting Help

If you encounter database issues not covered here:

1. Check server logs for detailed error messages
2. Run integrity check: `sqlite3 <db> "PRAGMA integrity_check;"`
3. Verify schema: `sqlite3 <db> "PRAGMA table_info(memories);"`
4. Report issue at: https://github.com/doobidoo/mcp-memory-service/issues

Include:
- Error messages from server logs
- Output from integrity_check
- Schema output
- Transfer method used (if applicable)
- Source and destination platforms
