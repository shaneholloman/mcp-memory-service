# Maintenance Scripts

This directory contains maintenance and diagnostic scripts for the MCP Memory Service database.

## Quick Reference

| Script | Purpose | Performance | Use Case |
|--------|---------|-------------|----------|
| [`regenerate_embeddings.py`](#regenerate_embeddingspy) | Regenerate all embeddings | ~5min for 2600 memories | After cosine migration or embedding corruption |
| [`fast_cleanup_duplicates.sh`](#fast_cleanup_duplicatessh) | Fast duplicate removal | <5s for 100+ duplicates | Bulk duplicate cleanup |
| [`find_all_duplicates.py`](#find_all_duplicatespy) | Detect near-duplicates | <2s for 2000 memories | Duplicate detection and analysis |
| [`find_duplicates.py`](#find_duplicatespy) | API-based duplicate finder | Slow (~90s/duplicate) | Detailed duplicate analysis via API |
| [`repair_sqlite_vec_embeddings.py`](#repair_sqlite_vec_embeddingspy) | Fix embedding corruption | Varies | Repair corrupted embeddings |
| [`repair_zero_embeddings.py`](#repair_zero_embeddingspy) | Fix zero-valued embeddings | Varies | Repair zero embeddings |
| [`cleanup_corrupted_encoding.py`](#cleanup_corrupted_encodingpy) | Fix encoding issues | Varies | Repair encoding corruption |

## Detailed Documentation

### `regenerate_embeddings.py`

**Purpose**: Regenerates embeddings for all memories in the database after schema migrations or corruption.

**When to Use**:
- After cosine distance migration
- When embeddings table is dropped but memories are preserved
- After embedding corruption detected

**Usage**:
```bash
/home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/regenerate_embeddings.py
```

**Performance**: ~5 minutes for 2600 memories with all-MiniLM-L6-v2 model

**Notes**:
- Uses configured storage backend (hybrid, cloudflare, or sqlite_vec)
- Creates embeddings using sentence-transformers model
- Shows progress every 100 memories
- Safe to run multiple times (idempotent)

---

### `fast_cleanup_duplicates.sh`

**Purpose**: Fast duplicate removal using direct SQL access instead of API calls.

**When to Use**:
- Bulk duplicate cleanup after detecting duplicates
- When API-based deletion is too slow (>1min per duplicate)
- Production cleanup without extended downtime

**Usage**:
```bash
bash scripts/maintenance/fast_cleanup_duplicates.sh
```

**Performance**: <5 seconds for 100+ duplicates

**How It Works**:
1. Stops HTTP server to avoid database locking
2. Uses direct SQL DELETE with timestamp normalization
3. Keeps newest copy of each duplicate group
4. Restarts HTTP server automatically

**Warnings**:
- ⚠️ Requires systemd HTTP server setup (`mcp-memory-http.service`)
- ⚠️ Brief service interruption during cleanup
- ⚠️ Direct database access bypasses Cloudflare sync (background sync handles it later)

---

### `find_all_duplicates.py`

**Purpose**: Fast duplicate detection using content normalization and hash comparison.

**When to Use**:
- Regular duplicate audits
- Before running cleanup operations
- Investigating duplicate memory issues

**Usage**:
```bash
/home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/find_all_duplicates.py
```

**Performance**: <2 seconds for 2000 memories

**Detection Method**:
- Normalizes content by removing timestamps (dates, ISO timestamps)
- Groups memories by MD5 hash of normalized content
- Reports duplicate groups with counts

**Output**:
```
Found 23 groups of duplicates
Total memories to delete: 115
Total memories after cleanup: 1601
```

---

### `find_duplicates.py`

**Purpose**: Comprehensive duplicate detection via HTTP API with detailed analysis.

**When to Use**:
- Need detailed duplicate analysis with full metadata
- API-based workflow required
- Integration with external tools

**Usage**:
```bash
/home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/find_duplicates.py
```

**Performance**: Slow (~90 seconds per duplicate deletion)

**Features**:
- Loads configuration from Claude hooks config
- Supports self-signed SSL certificates
- Pagination support for large datasets
- Detailed duplicate grouping and reporting

**Notes**:
- 15K script with comprehensive error handling
- Useful for API integration scenarios
- Slower than `find_all_duplicates.py` due to network overhead

---

### `repair_sqlite_vec_embeddings.py`

**Purpose**: Repairs corrupted embeddings in the sqlite-vec virtual table.

**When to Use**:
- Embedding corruption detected
- vec0 extension errors
- Database integrity issues

**Usage**:
```bash
/home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/repair_sqlite_vec_embeddings.py
```

**Warnings**:
- ⚠️ Requires vec0 extension to be properly installed
- ⚠️ May drop and recreate embeddings table

---

### `repair_zero_embeddings.py`

**Purpose**: Detects and fixes memories with zero-valued embeddings.

**When to Use**:
- Search results showing 0% similarity scores
- After embedding regeneration failures
- Embedding quality issues

**Usage**:
```bash
/home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/repair_zero_embeddings.py
```

---

### `cleanup_corrupted_encoding.py`

**Purpose**: Fixes encoding corruption issues in memory content.

**When to Use**:
- UTF-8 encoding errors
- Display issues with special characters
- After data migration from different encoding

**Usage**:
```bash
/home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/cleanup_corrupted_encoding.py
```

---

## Best Practices

### Before Running Maintenance Scripts

1. **Backup your database**:
   ```bash
   cp ~/.local/share/mcp-memory/sqlite_vec.db ~/.local/share/mcp-memory/sqlite_vec.db.backup
   ```

2. **Check memory count**:
   ```bash
   sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db "SELECT COUNT(*) FROM memories"
   ```

3. **Stop HTTP server if needed** (for direct database access):
   ```bash
   systemctl --user stop mcp-memory-http.service
   ```

### After Running Maintenance Scripts

1. **Verify results**:
   ```bash
   sqlite3 ~/.local/share/mcp-memory/sqlite_vec.db "SELECT COUNT(*) FROM memories"
   ```

2. **Check for duplicates**:
   ```bash
   /home/hkr/repositories/mcp-memory-service/venv/bin/python scripts/maintenance/find_all_duplicates.py
   ```

3. **Restart HTTP server**:
   ```bash
   systemctl --user start mcp-memory-http.service
   ```

4. **Test search functionality**:
   ```bash
   curl -s "http://127.0.0.1:8000/api/health"
   ```

### Performance Comparison

| Operation | API-based | Direct SQL | Speedup |
|-----------|-----------|------------|---------|
| Delete 1 duplicate | ~90 seconds | ~0.05 seconds | **1800x faster** |
| Delete 100 duplicates | ~2.5 hours | <5 seconds | **1800x faster** |
| Find duplicates | ~30 seconds | <2 seconds | **15x faster** |

**Recommendation**: Use direct SQL scripts (`fast_cleanup_duplicates.sh`, `find_all_duplicates.py`) for production maintenance. API-based scripts are useful for integration and detailed analysis.

## Troubleshooting

### "Database is locked"

**Cause**: HTTP server or MCP server has open connection

**Solution**:
```bash
# Stop HTTP server
systemctl --user stop mcp-memory-http.service

# Disconnect MCP server in Claude Code
# Type: /mcp

# Run maintenance script
bash scripts/maintenance/fast_cleanup_duplicates.sh

# Restart services
systemctl --user start mcp-memory-http.service
```

### "No such module: vec0"

**Cause**: Python sqlite3 module doesn't load vec0 extension automatically

**Solution**: Use scripts that work with the vec0-enabled environment:
- ✅ Use: `fast_cleanup_duplicates.sh` (bash wrapper with Python)
- ✅ Use: `/venv/bin/python` with proper storage backend
- ❌ Avoid: Direct `sqlite3` Python module for virtual table operations

### Slow API Performance

**Cause**: Hybrid backend syncs each operation to Cloudflare

**Solution**: Use direct SQL scripts for bulk operations:
```bash
bash scripts/maintenance/fast_cleanup_duplicates.sh  # NOT Python API scripts
```

## Related Documentation

- [Database Schema](../../docs/database-schema.md) - sqlite-vec table structure
- [Storage Backends](../../CLAUDE.md#storage-backends) - Hybrid, Cloudflare, SQLite-vec
- [Troubleshooting](../../docs/troubleshooting.md) - Common issues and solutions

## Contributing

When adding new maintenance scripts:

1. Add comprehensive docstring explaining purpose and usage
2. Include progress indicators for long-running operations
3. Add error handling and validation
4. Document in this README with performance characteristics
5. Test with both sqlite_vec and hybrid backends
