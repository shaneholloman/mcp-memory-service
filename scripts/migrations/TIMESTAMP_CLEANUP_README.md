# MCP Memory Timestamp Cleanup Scripts

## Overview

These scripts help clean up the timestamp mess in your MCP Memory ChromaDB database where multiple timestamp formats and fields have accumulated over time.

## Files

1. **`verify_mcp_timestamps.py`** - Verification script to check current timestamp state
2. **`cleanup_mcp_timestamps.py`** - Migration script to fix timestamp issues

## The Problem

Your database has accumulated 8 different timestamp-related fields:
- `timestamp` (integer) - Original design
- `created_at` (float) - Duplicate data
- `created_at_iso` (string) - ISO format duplicate
- `timestamp_float` (float) - Another duplicate
- `timestamp_str` (string) - String format duplicate
- `updated_at` (float) - Update tracking
- `updated_at_iso` (string) - Update tracking in ISO
- `date` (generic) - Generic date field

This causes:
- 3x storage overhead for the same timestamp
- Confusion about which field to use
- Inconsistent data retrieval

## Usage

### Step 1: Verify Current State

```bash
python3 scripts/migrations/verify_mcp_timestamps.py
```

This will show:
- Total memories in database
- Distribution of timestamp fields
- Memories missing timestamps
- Sample values showing the redundancy
- Date ranges for each timestamp type

### Step 2: Run Migration

```bash
python3 scripts/migrations/cleanup_mcp_timestamps.py
```

The migration will:
1. **Create a backup** of your database
2. **Standardize** all timestamps to integer format in the `timestamp` field
3. **Remove** all redundant timestamp fields
4. **Ensure** all memories have valid timestamps
5. **Optimize** the database with VACUUM

### Step 3: Verify Results

```bash
python3 scripts/migrations/verify_mcp_timestamps.py
```

After migration, you should see:
- Only one timestamp field (`timestamp`)
- All memories have timestamps
- Clean data structure

## Safety

- The migration script **always creates a backup** before making changes
- Backup location: `/Users/hkr/Library/Application Support/mcp-memory/chroma_db/chroma.sqlite3.backup_YYYYMMDD_HHMMSS`
- If anything goes wrong, you can restore the backup

## Restoration (if needed)

If you need to restore from backup:

```bash
# Stop Claude Desktop first
cp "/path/to/backup" "/Users/hkr/Library/Application Support/mcp-memory/chroma_db/chroma.sqlite3"
```

## After Migration

Update your MCP Memory Service code to only use the `timestamp` field (integer format) for all timestamp operations. This prevents the issue from recurring.
