# Docker Boot Loop Fix

This document describes the fix for issue #52 where the MCP Memory Service Docker container was experiencing a boot loop.

## Problem

The Docker container was exiting with code 0 immediately after successful initialization, causing Docker to continuously restart it. This happened because:

1. The MCP server uses stdio for communication with clients
2. When no client is connected (as in standalone Docker), the stdio streams close immediately
3. The server exits gracefully (code 0) when stdio closes
4. Docker's restart policy causes it to restart, creating an infinite loop

## Solution

We implemented a multi-part solution:

### 1. Standalone Mode

Added a new standalone mode for Docker deployments without an active MCP client:

```bash
# Use the standalone docker-compose file
docker-compose -f docker-compose.standalone.yml up
```

This mode:
- Sets `MCP_STANDALONE_MODE=1` environment variable
- Uses a special persistent entrypoint script
- Keeps the server running without requiring stdio communication

### 2. Improved Entrypoint Scripts

**docker-entrypoint.sh**: Enhanced to handle stdio better
- Detects standalone mode and switches to persistent entrypoint
- Implements a keep-alive mechanism for stdin
- Better signal handling for graceful shutdown

**docker-entrypoint-persistent.sh**: New script for standalone mode
- Creates named pipes for stdio simulation
- Keeps the stdin pipe open to prevent server exit
- Sends periodic heartbeats

### 3. Server Code Updates

Modified `server.py` to detect and handle standalone mode:
- Checks for `MCP_STANDALONE_MODE` environment variable
- In standalone mode, runs an infinite loop instead of stdio server
- Provides periodic heartbeat logging

### 4. Telemetry Fixes

Disabled ChromaDB telemetry to prevent initialization errors:
- Set `CHROMA_TELEMETRY_IMPL=none`
- Set `ANONYMIZED_TELEMETRY=false`

## Usage

### For MCP Client Integration (Claude Desktop)

Use the standard docker-compose:
```bash
docker-compose up
```

### For Standalone Deployment

Use the standalone configuration:
```bash
docker-compose -f docker-compose.standalone.yml up
```

### Environment Variables

- `MCP_STANDALONE_MODE=1`: Enable standalone mode (no MCP client required)
- `CHROMA_TELEMETRY_IMPL=none`: Disable ChromaDB telemetry
- `DOCKER_CONTAINER=1`: Automatically set to indicate Docker environment

## Testing

To verify the fix:

1. Build the Docker image:
   ```bash
   docker-compose build
   ```

2. Run in standalone mode:
   ```bash
   docker-compose -f docker-compose.standalone.yml up
   ```

3. Check logs for successful initialization without restarts:
   ```bash
   docker-compose logs -f
   ```

4. Verify the container stays running:
   ```bash
   docker ps
   ```

The container should initialize once and continue running without restarting.