# Litestream Sync - Local Network HTTP API Synchronization

Git-like staging workflow for syncing local SQLite-vec database to a central HTTP API server on your local network.

## Overview

This synchronization system enables **multi-device local network synchronization** using a central MCP Memory Service HTTP API as the remote source of truth. Unlike Cloudflare hybrid sync (which uses cloud infrastructure), Litestream sync is designed for:

- **Local network deployments** (e.g., home server, office network)
- **Privacy-focused setups** where data stays on your network
- **Centralized SQLite-vec backend** accessible via HTTP API
- **Multi-device synchronization** across machines on the same network

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌──────────────────┐
│   Local Device  │         │  Staging DB     │         │  Central Server  │
│  SQLite-vec DB  │◄───────►│  (Git-like)     │◄───────►│  HTTP API        │
│                 │  Stash  │                 │  Sync   │  SQLite-vec      │
└─────────────────┘         └─────────────────┘         └──────────────────┘
                                                          https://narrowbox.local:8443
```

**Components:**
- **Local Database**: Your working SQLite-vec database
- **Staging Database**: Git-like staging area for conflict detection (`~/Library/Application Support/mcp-memory/sqlite_vec_staging.db`)
- **Central Server**: Remote HTTP API serving as source of truth

## Workflow

The sync system follows a **Git-like workflow**:

1. **Stash** - Save local changes to staging database
2. **Pull** - Fetch latest changes from remote API
3. **Apply** - Apply staged changes back to local database
4. **Push** - Send changes to remote API

```bash
# Full sync workflow (recommended)
./memory_sync.sh sync

# Individual operations
./memory_sync.sh stash   # Save local changes
./memory_sync.sh pull    # Fetch remote changes
./memory_sync.sh apply   # Apply staged changes
./memory_sync.sh push    # Push to remote

# Check status
./memory_sync.sh status
```

## Setup

### 1. Initialize Local Litestream

```bash
./setup_local_litestream.sh
```

This script:
- Creates staging database schema
- Initializes sync tracking tables
- Sets up conflict detection system

### 2. Configure Remote API

Set the remote API endpoint and credentials:

```bash
export MCP_API_KEY="your-api-key"
export REMOTE_API="https://narrowbox.local:8443/api/memories"
```

### 3. Setup Remote Server (Optional)

If setting up the central server:

```bash
./setup_remote_litestream.sh
```

### 4. Configure Automatic Sync (macOS)

Install the launchd service for automatic replication:

```bash
# Copy service file
cp io.litestream.replication.plist ~/Library/LaunchAgents/

# Edit paths in the plist file to match your setup
# Then load the service
launchctl load ~/Library/LaunchAgents/io.litestream.replication.plist
```

## Scripts Reference

### Main Orchestrator

**`memory_sync.sh`** - Main sync coordinator
```bash
./memory_sync.sh sync     # Full sync workflow
./memory_sync.sh status   # Show sync status
./memory_sync.sh push     # Quick push only
./memory_sync.sh pull     # Quick pull only
./memory_sync.sh help     # Show help
```

### Core Operations

**`stash_local_changes.sh`** - Save local changes to staging
- Detects INSERT, UPDATE, DELETE operations
- Compares local vs staging database
- Marks changes for sync

**`pull_remote_changes.sh`** - Fetch from remote API
- Retrieves latest memories from HTTP API
- Stores in staging database
- Detects conflicts with local changes

**`apply_local_changes.sh`** - Apply staged changes locally
- Applies non-conflicting changes to local database
- Preserves conflict-marked entries for manual resolution
- Updates sync timestamps

**`push_to_remote.sh`** - Push to remote API
- Sends staged changes to remote HTTP API
- Handles API authentication (MCP_API_KEY)
- Retries failed pushes
- Marks successful syncs

### Conflict Resolution

**`resolve_conflicts.sh`** - Manual conflict resolution
- Lists detected conflicts
- Allows choosing remote or local version
- Updates staging database accordingly

### Utilities

**`manual_sync.sh`** - Manual sync trigger (macOS automation)
**`sync_from_remote.sh`** - Pull-only sync from remote
**`sync_from_remote_noconfig.sh`** - Pull without config file

## Configuration

### Environment Variables

```bash
# Required
export MCP_API_KEY="your-api-key"               # API authentication
export REMOTE_API="https://server:8443/api/memories"  # Remote endpoint

# Optional
export STAGING_DB="/custom/path/staging.db"     # Custom staging DB path
export HOSTNAME="my-device"                     # Device identifier
```

### Staging Database Location

Default: `~/Library/Application Support/mcp-memory/sqlite_vec_staging.db` (macOS)
Linux: `~/.local/share/mcp-memory/sqlite_vec_staging.db`

### Database Schema

The staging database (`staging_db_init.sql`) includes:
- `staged_memories` - Staged changes with conflict tracking
- `sync_status` - Sync metadata and timestamps
- `conflict_resolution` - Manual resolution tracking

## Conflict Detection

The system detects conflicts when:
- Same memory modified both locally and remotely
- Timestamps differ between local and remote versions
- Content hashes don't match

**Conflict Resolution:**
```bash
# List conflicts
./memory_sync.sh status

# Resolve manually
./resolve_conflicts.sh

# Options:
# 1. Keep local version
# 2. Use remote version
# 3. Merge manually
```

## Monitoring

### Check Sync Status
```bash
./memory_sync.sh status
```

**Output:**
- Staged changes ready: Count of changes to push
- Conflicts detected: Count requiring resolution
- Failed pushes: Count of retry-pending changes
- Last remote sync: Timestamp of last pull
- Last push attempt: Timestamp of last push

### Logs

Litestream replication logs (macOS):
```bash
tail -f /var/log/litestream.log
```

## Comparison: Litestream vs Cloudflare Sync

| Feature | Litestream Sync | Cloudflare Hybrid Sync |
|---------|----------------|------------------------|
| **Backend** | Local network HTTP API | Cloudflare Workers (cloud) |
| **Network** | LAN/private network | Internet (global) |
| **Staging** | Git-like staging DB | Direct sync queue |
| **Privacy** | Data stays on network | Data in Cloudflare cloud |
| **Setup** | Self-hosted server | Cloudflare account needed |
| **Latency** | LAN speed (~1-5ms) | Network dependent (50-200ms) |
| **Conflicts** | Manual resolution | Last-write-wins |

**Use Litestream when:**
- You want data to stay on your local network
- You have a central server (NAS, home server)
- You need multi-device sync within your home/office
- You prefer manual conflict resolution

**Use Cloudflare when:**
- You need global access from anywhere
- You want automatic cloud backup
- You prefer zero-maintenance sync
- You're okay with data in cloud infrastructure

## Troubleshooting

### Staging database not found
```bash
./setup_local_litestream.sh  # Re-initialize
```

### Cannot connect to remote API
```bash
# Test connectivity
curl -k https://narrowbox.local:8443/api/health

# Check API key
echo $MCP_API_KEY

# Verify remote server is running
ssh server "systemctl status mcp-memory"
```

### Conflicts not resolving
```bash
# Manual resolution
./resolve_conflicts.sh

# Or reset staging (WARNING: loses pending changes)
rm "$STAGING_DB"
./setup_local_litestream.sh
```

### Push failures
```bash
# Check staging database
./memory_sync.sh status

# Retry push
./memory_sync.sh push

# Check failed entries
sqlite3 "$STAGING_DB" "SELECT * FROM staged_memories WHERE conflict_status = 'push_failed';"
```

## Advanced Usage

### Custom Sync Interval (macOS)

Edit `io.litestream.replication.plist`:
```xml
<key>StartInterval</key>
<integer>300</integer>  <!-- 5 minutes -->
```

### Selective Sync

Modify staging queries to filter by tags or date:
```bash
# Edit stash_local_changes.sh
# Add WHERE clause to filter memories
WHERE tags LIKE '%work%'  # Only sync work-tagged memories
```

### Multiple Remote Servers

Run separate staging databases for each remote:
```bash
export STAGING_DB="$HOME/.mcp-memory/staging-server1.db"
./memory_sync.sh sync

export STAGING_DB="$HOME/.mcp-memory/staging-server2.db"
./memory_sync.sh sync
```

## Migration from Litestream to Cloudflare

If migrating to Cloudflare hybrid sync:

1. **Final sync to central server**
   ```bash
   ./memory_sync.sh sync
   ```

2. **Export all memories**
   ```bash
   python scripts/sync/export_memories.py
   ```

3. **Switch to Cloudflare backend**
   ```bash
   export MCP_MEMORY_STORAGE_BACKEND=cloudflare
   # Set Cloudflare credentials
   ```

4. **Import memories to Cloudflare**
   ```bash
   python scripts/sync/import_memories.py memories_export.json
   ```

## Files Reference

- `memory_sync.sh` - Main orchestrator
- `stash_local_changes.sh` - Stash operation
- `pull_remote_changes.sh` - Pull operation
- `apply_local_changes.sh` - Apply operation
- `push_to_remote.sh` - Push operation
- `resolve_conflicts.sh` - Conflict resolution
- `setup_local_litestream.sh` - Local setup
- `setup_remote_litestream.sh` - Remote setup
- `staging_db_init.sql` - Database schema
- `io.litestream.replication.plist` - macOS service
- `manual_sync.sh` - Manual trigger
- `sync_from_remote.sh` - Pull-only sync
- `sync_from_remote_noconfig.sh` - Pull without config

## Support

For issues or questions:
- Check troubleshooting section above
- Review main project documentation
- Ensure remote API is running and accessible
- Verify network connectivity and firewall rules
