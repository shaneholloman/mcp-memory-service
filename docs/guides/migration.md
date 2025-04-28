# Memory Migration Guide

This guide provides step-by-step instructions for migrating memories between different ChromaDB instances using the MCP Memory Service.

## Prerequisites

Before starting the migration process, ensure you have:

1. Python 3.10 or later installed
2. Required packages installed (check `requirements.txt`)
3. Access to both source and target ChromaDB instances
4. Sufficient disk space for local migrations
5. Network access for remote migrations

## Step 1: Environment Verification

First, verify your environment is properly configured:

```bash
python scripts/verify_environment.py
```

This will check:
- Python version compatibility
- Required package installations
- ChromaDB paths and configurations
- Network connectivity (for remote migrations)

## Step 2: Choose Migration Type

### Option A: Local to Remote Migration
Use this option to move memories from your local development environment to a remote production server.

### Option B: Remote to Local Migration
Use this option to create local backups or set up a development environment with existing memories.

## Step 3: Prepare Configuration

### For Local to Remote Migration
1. Identify your local ChromaDB path
2. Note the remote server's host and port
3. Prepare the configuration:
```json
{
    "source_type": "local",
    "source_config": "/path/to/local/chroma",
    "target_type": "remote",
    "target_config": {
        "host": "remote-host",
        "port": 8000
    }
}
```

### For Remote to Local Migration
1. Note the remote server's host and port
2. Choose a local path for the ChromaDB
3. Prepare the configuration:
```json
{
    "source_type": "remote",
    "source_config": {
        "host": "remote-host",
        "port": 8000
    },
    "target_type": "local",
    "target_config": "/path/to/local/chroma"
}
```

## Step 4: Run Migration

### Using Command Line
```bash
# Local to Remote Migration
python scripts/mcp-migration.py \
    --source-type local \
    --source-config /path/to/local/chroma \
    --target-type remote \
    --target-config '{"host": "remote-host", "port": 8000}'

# Remote to Local Migration
python scripts/mcp-migration.py \
    --source-type remote \
    --source-config '{"host": "remote-host", "port": 8000}' \
    --target-type local \
    --target-config /path/to/local/chroma
```

### Using Python Script
```python
from scripts.mcp_migration import migrate_memories

# Local to Remote Migration
migrate_memories(
    source_type='local',
    source_config='/path/to/local/chroma',
    target_type='remote',
    target_config={'host': 'remote-host', 'port': 8000}
)

# Remote to Local Migration
migrate_memories(
    source_type='remote',
    source_config={'host': 'remote-host', 'port': 8000},
    target_type='local',
    target_config='/path/to/local/chroma'
)
```

## Step 5: Monitor Progress

The migration script provides detailed logging:
- Connection status
- Collection verification
- Batch processing progress
- Error messages (if any)

Monitor the output for:
- Successful connection messages
- Batch processing updates
- Any error messages
- Final verification results

## Step 6: Verify Migration

After migration completes:
1. Check the target collection for expected number of memories
2. Verify a sample of memories for content integrity
3. Test memory access through the MCP Memory Service

## Troubleshooting

### Common Issues

1. **Connection Failures**
   - Verify network connectivity
   - Check firewall settings
   - Validate host and port configurations

2. **Permission Issues**
   - Check file permissions for local paths
   - Verify user access rights
   - Ensure proper directory ownership

3. **Data Transfer Errors**
   - Check disk space
   - Verify collection permissions
   - Monitor system resources

### Error Messages

1. **"Failed to connect to ChromaDB"**
   - Verify ChromaDB is running
   - Check network connectivity
   - Validate configuration

2. **"Collection not found"**
   - Verify collection name
   - Check collection permissions
   - Ensure collection exists

3. **"Insufficient disk space"**
   - Free up disk space
   - Choose a different target location
   - Consider cleaning up old data

## Best Practices

1. **Before Migration**
   - Backup existing data
   - Verify environment compatibility
   - Check system resources

2. **During Migration**
   - Monitor progress
   - Avoid interrupting the process
   - Check for error messages

3. **After Migration**
   - Verify data integrity
   - Test memory access
   - Document the migration

## Additional Resources

- [Technical Documentation](technical/memory-migration.md) - Detailed technical information
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
- [Configuration Guide](../README.md#configuration-options) - Available settings and options 