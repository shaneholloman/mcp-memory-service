# ChromaDB to SQLite-vec Migration Guide

This guide walks you through migrating your existing ChromaDB memories to the new SQLite-vec backend.

## Why Migrate?

SQLite-vec offers several advantages over ChromaDB for the MCP Memory Service:

- **Lightweight**: Single file database, no external dependencies
- **Faster startup**: No collection initialization overhead
- **Better performance**: Optimized for small to medium datasets
- **Simpler deployment**: No persistence directory management
- **Cross-platform**: Works consistently across all platforms
- **HTTP/SSE support**: New web interface only works with SQLite-vec

## Migration Methods

### Method 1: Automated Migration Script (Recommended)

Use the provided migration script for a safe, automated migration:

```bash
# Run the migration script
python scripts/migrate_chroma_to_sqlite.py
```

The script will:
- ✅ Check your existing ChromaDB data
- ✅ Count all memories to migrate
- ✅ Ask for confirmation before proceeding
- ✅ Migrate memories in batches with progress tracking
- ✅ Skip duplicates if running multiple times
- ✅ Verify migration completed successfully
- ✅ Provide next steps

### Method 2: Manual Configuration Switch

If you want to start fresh with SQLite-vec (losing existing memories):

```bash
# Set the storage backend to SQLite-vec
export MCP_MEMORY_STORAGE_BACKEND=sqlite_vec

# Optionally set custom database path
export MCP_MEMORY_SQLITE_PATH=/path/to/your/memory.db

# Restart MCP Memory Service
```

## Step-by-Step Migration

### 1. Backup Your Data (Optional but Recommended)

```bash
# Create a backup of your ChromaDB data
cp -r ~/.mcp_memory_chroma ~/.mcp_memory_chroma_backup
```

### 2. Run Migration Script

```bash
cd /path/to/mcp-memory-service
python scripts/migrate_chroma_to_sqlite.py
```

**Example Output:**
```
🚀 MCP Memory Service - ChromaDB to SQLite-vec Migration
============================================================

📂 ChromaDB source: /Users/you/.mcp_memory_chroma
📂 SQLite-vec destination: /Users/you/.mcp_memory/memory_migrated.db

🔍 Checking ChromaDB data...
✅ Found 1,247 memories in ChromaDB

⚠️  About to migrate 1,247 memories from ChromaDB to SQLite-vec
📝 Destination file: /Users/you/.mcp_memory/memory_migrated.db

Proceed with migration? (y/N): y

🔌 Connecting to ChromaDB...
🔌 Connecting to SQLite-vec...
📥 Fetching all memories from ChromaDB...
🔄 Processing batch 1/25 (50 memories)...
✅ Batch 1 complete. Progress: 50/1,247

... (migration progress) ...

🎉 Migration completed successfully!

📊 MIGRATION SUMMARY
====================================
Total memories found:     1,247
Successfully migrated:    1,247
Duplicates skipped:       0
Failed migrations:        0
Migration duration:       45.32 seconds
```

### 3. Update Configuration

After successful migration, update your environment:

```bash
# Switch to SQLite-vec backend
export MCP_MEMORY_STORAGE_BACKEND=sqlite_vec

# Set the database path (use the path shown in migration output)
export MCP_MEMORY_SQLITE_PATH=/path/to/memory_migrated.db
```

**For permanent configuration, add to your shell profile:**

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.profile
echo 'export MCP_MEMORY_STORAGE_BACKEND=sqlite_vec' >> ~/.bashrc
echo 'export MCP_MEMORY_SQLITE_PATH=/path/to/memory_migrated.db' >> ~/.bashrc
```

### 4. Restart and Test

```bash
# If using Claude Desktop, restart Claude Desktop application
# If using MCP server directly, restart the server

# Test that migration worked
python scripts/verify_environment.py
```

### 5. Enable HTTP/SSE Interface (Optional)

To use the new web interface:

```bash
# Enable HTTP server
export MCP_HTTP_ENABLED=true
export MCP_HTTP_PORT=8000

# Start HTTP server
python scripts/run_http_server.py

# Open browser to http://localhost:8000
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_MEMORY_STORAGE_BACKEND` | Storage backend (`chroma` or `sqlite_vec`) | `chroma` |
| `MCP_MEMORY_SQLITE_PATH` | SQLite-vec database file path | `~/.mcp_memory/sqlite_vec.db` |
| `MCP_HTTP_ENABLED` | Enable HTTP/SSE interface | `false` |
| `MCP_HTTP_PORT` | HTTP server port | `8000` |

### Claude Desktop Configuration

Update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-memory-service",
        "run",
        "memory"
      ],
      "env": {
        "MCP_MEMORY_STORAGE_BACKEND": "sqlite_vec",
        "MCP_MEMORY_SQLITE_PATH": "/path/to/memory_migrated.db"
      }
    }
  }
}
```

## Troubleshooting

### Migration Issues

**"No memories found in ChromaDB"**
- Check that `MCP_MEMORY_CHROMA_PATH` points to correct directory
- Verify ChromaDB data exists: `ls -la ~/.mcp_memory_chroma`

**"Failed to migrate memory"**
- Migration continues with other memories
- Check logs for specific error details
- Re-run migration script (duplicates will be skipped)

**"Migration verification failed"**
- Some memories may have failed to migrate
- Check error summary in migration output
- Consider re-running migration

### Runtime Issues

**"Storage backend not found"**
- Ensure `MCP_MEMORY_STORAGE_BACKEND=sqlite_vec`
- Check that SQLite-vec dependencies are installed

**"Database file not found"**
- Verify `MCP_MEMORY_SQLITE_PATH` points to migrated database
- Check file permissions

### Performance Comparison

| Aspect | ChromaDB | SQLite-vec |
|--------|----------|------------|
| Startup time | ~2-3 seconds | ~0.5 seconds |
| Memory usage | ~100-200MB | ~20-50MB |
| Storage | Directory + files | Single file |
| Dependencies | chromadb, sqlite | sqlite-vec only |
| Scalability | Better for >10k memories | Optimal for <10k memories |

## Rollback Plan

If you need to switch back to ChromaDB:

```bash
# Switch back to ChromaDB
export MCP_MEMORY_STORAGE_BACKEND=chroma
unset MCP_MEMORY_SQLITE_PATH

# Restart MCP Memory Service
```

Your original ChromaDB data remains unchanged during migration.

## Next Steps

After successful migration:

1. ✅ Test memory operations (store, retrieve, search)
2. ✅ Try the HTTP/SSE interface for real-time updates
3. ✅ Update any scripts or tools that reference storage paths
4. ✅ Consider backing up your new SQLite-vec database regularly
5. ✅ Remove old ChromaDB data after confirming migration success

## Support

If you encounter issues:
1. Check the migration output and error messages
2. Verify environment variables are set correctly
3. Test with a small subset of data first
4. Review logs for detailed error information

The migration preserves all your data including:
- Memory content and metadata
- Tags and timestamps
- Content hashes (for deduplication)
- Semantic embeddings (regenerated with same model)