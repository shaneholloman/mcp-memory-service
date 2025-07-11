# Docker Boot Loop Fix

## Issue Description
The MCP Memory Service was experiencing a boot loop in Docker containers where the process would exit with code 0 immediately after initialization. This was caused by the stdio-based MCP server not properly maintaining its event loop when running in a containerized environment.

## Root Causes
1. **Missing TTY Configuration**: Docker containers need `stdin_open: true` and `tty: true` for proper stdio handling
2. **Event Loop Exit**: The MCP server's `run()` method was completing immediately without blocking
3. **No Process Persistence**: The subprocess calls in wrapper scripts weren't handling the server lifecycle correctly
4. **Missing Signal Handling**: No proper signal handlers for graceful shutdown in Docker

## Fixes Applied

### 1. Docker Compose Configuration
Added TTY settings to all docker-compose files:
```yaml
stdin_open: true
tty: true
```

### 2. Server Process Handling
- Added Docker environment detection
- Improved error handling and logging for stdio operations
- Added proper signal handlers (SIGTERM, SIGINT) for graceful shutdown

### 3. Docker Entrypoint Script
Created `/usr/local/bin/docker-entrypoint.sh` to:
- Handle signals properly
- Execute the correct startup command based on UV_ACTIVE
- Ensure the process stays alive with `exec`

### 4. Wrapper Script Improvements
- Modified `uv_wrapper.py` to use `subprocess.run()` instead of `check_call()`
- Added Docker environment detection
- Better error handling for subprocess failures

### 5. Dockerfile Updates
- Set `DOCKER_CONTAINER=1` environment variable
- Use the new entrypoint script
- Ensure proper permissions on stdio devices

## Testing the Fix
To test the Docker setup:

```bash
# Build and run with standard Docker Compose
docker-compose up --build

# Or with UV support
docker-compose -f docker-compose.uv.yml up --build

# Check if the container stays running
docker ps

# View logs
docker-compose logs -f
```

## Expected Behavior
- Container should start and remain running
- Logs should show "MCP Memory Service running in Docker container"
- No immediate exit with code 0
- Proper handling of SIGTERM for graceful shutdown