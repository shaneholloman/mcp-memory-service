# Docker Installation Guide

This guide provides detailed instructions for running the MCP Memory Service using Docker.

## Prerequisites

- Docker and Docker Compose installed on your system
- Basic knowledge of Docker concepts
- Sufficient disk space for Docker images and container volumes

## Quick Start

The simplest way to run the Memory Service is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/doobidoo/mcp-memory-service.git
cd mcp-memory-service

# Start the service
docker-compose up
```

This will:
- Build a Docker image for the Memory Service
- Create persistent volumes for the database and backups
- Start the service on port 8000

## Docker Compose Options

We provide multiple Docker Compose configurations to accommodate different environments and preferences:

### Standard Configuration (recommended for MCP clients)

**File**: `docker-compose.yml`

This configuration installs the package in development mode and is designed for use with MCP clients like Claude Desktop:

```bash
docker-compose up
```

### Standalone Configuration (recommended for testing/development)

**File**: `docker-compose.standalone.yml`

This configuration runs the service in standalone mode, which keeps the container running without requiring an active MCP client connection. This prevents the "boot loop" issue where the container exits immediately after initialization:

```bash
docker-compose -f docker-compose.standalone.yml up
```

Use this mode when:
- Testing the service without Claude Desktop
- Running the service for development purposes
- Deploying the service independently

### UV Package Manager Configuration

**File**: `docker-compose.uv.yml`

This configuration uses the UV package manager and the wrapper script, which matches the Dockerfile approach:

```bash
docker-compose -f docker-compose.uv.yml up
```

### PYTHONPATH Configuration

**File**: `docker-compose.pythonpath.yml`

This configuration explicitly sets the PYTHONPATH to include the source directory:

```bash
docker-compose -f docker-compose.pythonpath.yml up
```

## Environment Variables

You can customize the service by setting environment variables in your Docker Compose file:

```yaml
environment:
  - MCP_MEMORY_CHROMA_PATH=/app/chroma_db
  - MCP_MEMORY_BACKUPS_PATH=/app/backups
  - LOG_LEVEL=INFO
  - MAX_RESULTS_PER_QUERY=10
  - SIMILARITY_THRESHOLD=0.7
  - MCP_STANDALONE_MODE=1  # Enable standalone mode (no MCP client required)
  - CHROMA_TELEMETRY_IMPL=none  # Disable ChromaDB telemetry
  - ANONYMIZED_TELEMETRY=false  # Disable anonymous telemetry
```

## Volume Management

The service uses two persistent volumes:

1. **ChromaDB Volume**: Stores the vector database
   - Default path: `/app/chroma_db`
   - Maps to: `${CHROMA_DB_PATH:-$HOME/mcp-memory/chroma_db}`

2. **Backups Volume**: Stores database backups
   - Default path: `/app/backups`
   - Maps to: `${BACKUPS_PATH:-$HOME/mcp-memory/backups}`

You can customize these paths by setting environment variables before running Docker Compose:

```bash
export CHROMA_DB_PATH=/custom/path/to/chroma_db
export BACKUPS_PATH=/custom/path/to/backups
docker-compose up
```

## Building Custom Images

To build and run a custom Docker image manually:

```bash
# Build the image
docker build -t mcp-memory-service .

# Run the container
docker run -p 8000:8000 \
  -v /path/to/chroma_db:/app/chroma_db \
  -v /path/to/backups:/app/backups \
  -e LOG_LEVEL=INFO \
  mcp-memory-service
```

## Troubleshooting

### Docker Boot Loop Issue

If your container keeps restarting immediately after initialization (exit code 0), this is because the MCP server expects an active client connection via stdio. Solutions:

1. **Use standalone mode** (recommended for testing):
   ```bash
   docker-compose -f docker-compose.standalone.yml up
   ```

2. **Set standalone environment variable** in your docker-compose file:
   ```yaml
   environment:
     - MCP_STANDALONE_MODE=1
   ```

3. **For production use with Claude Desktop**, use the standard configuration which handles stdio properly:
   ```bash
   docker-compose up
   ```

### Module Not Found Error

If you see a `ModuleNotFoundError` for `mcp_memory_service`, it means the Python module is not in the Python path. Try:

1. Using the standard `docker-compose.yml` file which installs the package with `pip install -e .`
2. Using the `docker-compose.uv.yml` file which uses the wrapper script
3. Using the `docker-compose.pythonpath.yml` file which explicitly sets the PYTHONPATH

### Telemetry Errors

If you see ChromaDB telemetry errors during initialization, these are now automatically disabled in all Docker configurations. The errors are harmless but have been suppressed by setting:
- `CHROMA_TELEMETRY_IMPL=none`
- `ANONYMIZED_TELEMETRY=false`

### Port Conflicts

If port 8000 is already in use, modify the port mapping in the Docker Compose file:

```yaml
ports:
  - "8001:8000"  # Map container port 8000 to host port 8001
```

### Permission Issues

If you encounter permission issues with the volumes, ensure the host directories exist and have appropriate permissions:

```bash
mkdir -p ~/mcp-memory/chroma_db ~/mcp-memory/backups
chmod 777 ~/mcp-memory/chroma_db ~/mcp-memory/backups
```

## Performance Considerations

The Memory Service can be resource-intensive, especially when using larger embedding models. Consider these settings for optimal Docker performance:

1. Allocate sufficient memory to Docker (at least 2GB, 4GB+ recommended)
2. Use volume mounts on fast storage for better database performance
3. Set appropriate environment variables for your hardware:
   ```yaml
   environment:
     - MCP_MEMORY_BATCH_SIZE=4  # Smaller batch size for limited resources
     - MCP_MEMORY_FORCE_CPU=1   # Force CPU mode if GPU acceleration isn't needed
   ```

## Security Notes

- The Docker configuration exposes port 8000, which should not be accessible from the internet
- No authentication is provided by default; use appropriate network isolation
- The service is designed for local development and operation, not for production deployment

## Next Steps

After setting up the Docker container, you can:

1. Configure Claude to use the Memory Service (see [Claude Configuration Guide](claude_config.md))
2. Test the service by storing and retrieving memories
3. Customize the service settings for your specific needs