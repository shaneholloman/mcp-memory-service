# Memory Cleanup Script Documentation

## Overview

The `cleanup_memories.py` script is designed to identify and remove erroneous entries from the ChromaDB database used by the MCP Memory Service. This tool is particularly useful for cleaning up corrupted memories without having to reset the entire database.

## Location

This script should be placed in the `scripts` directory of your MCP Memory Service repository:

```
/Users/hkr/Documents/GitHub/mcp-memory-service/scripts/cleanup_memories.py
```

## Features

- Intelligently identifies potentially erroneous memory entries
- Supports targeted deletion using text pattern matching
- Provides a dry-run mode to preview changes before execution
- Includes a full reset option as an alternative to targeted cleanup
- Works with custom ChromaDB paths through environment variables

## Prerequisites

- Python 3.7+
- Access to the MCP Memory Service codebase
- Appropriate permissions to access and modify the ChromaDB directory

## Usage

### Basic Usage

To run the script with default settings (which will attempt to identify common error patterns):

```bash
cd /Users/hkr/Documents/GitHub/mcp-memory-service
python scripts/cleanup_memories.py
```

### Setting the ChromaDB Path

The script uses the `MCP_MEMORY_CHROMA_PATH` environment variable to determine where the ChromaDB is located:

```bash
export MCP_MEMORY_CHROMA_PATH="/path/to/your/chroma_db"
python scripts/cleanup_memories.py
```

### Available Options

| Option | Description |
|--------|-------------|
| `--error-text TEXT` | Specify a text pattern found in erroneous entries |
| `--dry-run` | Show what would be deleted without actually deleting |
| `--reset` | Completely reset the database (use with caution!) |

### Example Commands

#### Perform a Dry Run

To preview what entries would be deleted without making any changes:

```bash
python scripts/cleanup_memories.py --dry-run
```

#### Search for Specific Error Text

To find and remove entries containing specific error text:

```bash
python scripts/cleanup_memories.py --error-text "error pattern"
```

#### Reset the Entire Database

To completely reset the database (equivalent to using the `--reset` flag with the restore script):

```bash
python scripts/cleanup_memories.py --reset
```

## How It Works

1. **Initialization**: The script connects to the ChromaDB at the specified location.

2. **Entry Analysis**: In the absence of a specific error pattern, the script looks for:
   - Very short entries (less than 10 characters)
   - Entries containing common error terms ('error', 'exception', 'failed', 'invalid')

3. **Cleanup Process**: 
   - Identified entries are deleted in batches to avoid overwhelming the database
   - Progress and results are logged to the console

## Integration with Backup and Restore

This script complements the existing `restore_memories.py` script:

1. First restore your memories from backup:
   ```bash
   python scripts/restore_memories.py "/path/to/backup.json"
   ```

2. Then clean up any remaining erroneous entries:
   ```bash
   python scripts/cleanup_memories.py
   ```

## Troubleshooting

### Script Can't Find ChromaDB

If you encounter errors about the ChromaDB path:

1. Make sure you've set the `MCP_MEMORY_CHROMA_PATH` environment variable correctly
2. Verify that the path exists and is accessible
3. Check permissions on the ChromaDB directory

### No Erroneous Entries Found

If the script reports "No erroneous entries found" but you know there are problems:

1. Try specifying an `--error-text` parameter with a pattern you know exists in the bad entries
2. Check if your ChromaDB path is correct
3. Run a query directly against the database to confirm the presence of problematic entries

## Caution

- Always run with `--dry-run` first to preview changes
- Consider making a backup of your ChromaDB directory before running cleanup operations
- The `--reset` option will delete ALL memories in the database

## Logging

The script provides detailed logging to help track the cleanup process:
- Information about the total number of memories found
- Details about identified erroneous entries
- Progress updates during batch deletion
- Errors and warnings when issues are encountered
