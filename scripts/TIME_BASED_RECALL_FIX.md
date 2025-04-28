# Time-Based Recall Fix for MCP Memory Service

This guide explains how to fix the time-based recall functionality in the MCP Memory Service. The issue was identified in GitHub issue #19, where time-based recall queries were not working correctly due to inconsistent timestamp formats in the database.

## Understanding the Issue

The key problems were:

1. Timestamps were being stored in different formats (floats, float strings, integer strings)
2. When querying, the formats didn't match which caused no results to be returned
3. The `recall_by_timeframe` tool was missing proper implementation

## Fix Implementation

We've made the following changes to fix the issue:

1. Modified the `_format_metadata_for_chroma` method to store timestamps as integer timestamps
2. Updated the `recall` method to use integer timestamps in queries
3. Fixed the `handle_recall_by_timeframe` method implementation
4. Added proper logging to help diagnose any remaining issues

## Migration Process

For the fix to work properly, all existing memories need to be updated to use the new timestamp format. We've created scripts to handle this migration safely:

### Step 1: Create a Backup

Always start with a backup to ensure no data is lost:

```bash
python scripts/backup_memories.py
```

This will create a backup file in your configured backups directory with timestamp in the filename.

### Step 2: Run the Migration Script

The migration script updates all memory timestamps to the new format:

```bash
python scripts/migrate_timestamps.py
```

**Note**: If you encounter any errors related to embeddings or array truth values, the scripts have been designed to be resilient and will use fallback methods.

This script will:
- Read all memories from the database
- Convert their timestamps to integer strings
- Update each memory in the database
- Verify the migration was successful
- Test a time-based query to ensure it works

### Step 3: Verify Time-Based Recall Works

After running the migration, restart the MCP Memory Service and test time-based recall:

```bash
# Using recall_memory
mcp-memory-service.recall_memory({"query": "recall what I stored yesterday"})

# Using recall_by_timeframe
mcp-memory-service.recall_by_timeframe({
    "start_date": "2025-04-25", 
    "end_date": "2025-04-26"
})
```

## If Something Goes Wrong

If the migration causes any issues, you can restore from your backup:

```bash
python scripts/restore_memories.py memory_backup_YYYYMMDD_HHMMSS.json --reset
```

Use the `--reset` flag to completely reset the database before restoration.

## Technical Details

### New Timestamp Format

- All timestamps are now stored as integer timestamps (not strings)
- For example: `1714161600` instead of `1714161600.123` or `"1714161600"`
- This ensures ChromaDB can properly compare timestamps in queries

### Affected Files

- `src/mcp_memory_service/storage/chroma.py`
- `src/mcp_memory_service/server.py`

### Testing

After migration, you should be able to:
1. Create new memories and find them by time expressions
2. Recall older memories using time expressions
3. Use both natural language time expressions and explicit date ranges

## Summary

This fix brings full time-based recall functionality to the MCP Memory Service, allowing you to retrieve memories using natural language time expressions like "yesterday," "last week," or specific date ranges.

If you encounter any issues, please report them on the GitHub repository.
