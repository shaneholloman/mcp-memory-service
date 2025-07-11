# Docker Deployment

## Overview

The MCP Memory Service can be deployed using Docker for platform-agnostic installation and operation. The Docker configuration uses UV for dependency management, ensuring consistent performance across different environments.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for simplified deployment)

## Quick Start

### Using Docker Directly

```bash
# Build the Docker image
docker build -t mcp-memory-service .

# Create directories for persistent storage
mkdir -p ./data/chroma_db ./data/backups

# Run with default settings (for MCP clients)
docker run -d -p 8000:8000 --name memory-service \
  -v ./data/chroma_db:/app/chroma_db \
  -v ./data/backups:/app/backups \
  mcp-memory-service

# Run in standalone mode (for testing/development)
docker run -d -p 8000:8000 --name memory-service \
  -v ./data/chroma_db:/app/chroma_db \
  -v ./data/backups:/app/backups \
  -e MCP_STANDALONE_MODE=1 \
  mcp-memory-service
```

### Using Docker Compose

```bash
# Create data directories
mkdir -p ./data/chroma_db ./data/backups

# Start the service (for MCP clients like Claude Desktop)
docker-compose up -d

# Start in standalone mode (prevents boot loops)
docker-compose -f docker-compose.standalone.yml up -d
```

## Configuration Options

### Environment Variables

The Docker container supports the following environment variables:

| Variable | Description | Default |
|----------|-------------|--------|
| `MCP_MEMORY_CHROMA_PATH` | Path to ChromaDB storage | `/app/chroma_db` |
| `MCP_MEMORY_BACKUPS_PATH` | Path to backups storage | `/app/backups` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `MAX_RESULTS_PER_QUERY` | Maximum number of results returned per query | `10` |
| `SIMILARITY_THRESHOLD` | Threshold for similarity search | `0.7` |
| `MCP_MEMORY_FORCE_CPU` | Force CPU-only mode | `0` |
| `PYTORCH_ENABLE_MPS_FALLBACK` | Enable MPS fallback for Apple Silicon | `1` |
| `MCP_STANDALONE_MODE` | Enable standalone mode (no MCP client required) | `0` |
| `CHROMA_TELEMETRY_IMPL` | ChromaDB telemetry implementation | `none` |
| `ANONYMIZED_TELEMETRY` | Enable anonymous telemetry | `false` |

### Example: Custom Configuration

```bash
docker run -d -p 8000:8000 --name memory-service \
  -v ./data/chroma_db:/app/chroma_db \
  -v ./data/backups:/app/backups \
  -e MCP_MEMORY_CHROMA_PATH=/app/chroma_db \
  -e MCP_MEMORY_BACKUPS_PATH=/app/backups \
  -e LOG_LEVEL=DEBUG \
  -e MAX_RESULTS_PER_QUERY=20 \
  -e SIMILARITY_THRESHOLD=0.8 \
  mcp-memory-service
```

## Integration with Claude Desktop

To use the Docker container with Claude Desktop, update your `claude_desktop_config.json` file:

```json
{
  "memory": {
    "command": "docker",
    "args": [
      "run",
      "--rm",
      "-p", "8000:8000",
      "-v", "/path/to/data/chroma_db:/app/chroma_db",
      "-v", "/path/to/data/backups:/app/backups",
      "-e", "MCP_MEMORY_CHROMA_PATH=/app/chroma_db",
      "-e", "MCP_MEMORY_BACKUPS_PATH=/app/backups",
      "mcp-memory-service"
    ]
  }
}
```

## Data Persistence

The Docker configuration uses volumes to persist data:

- `/app/chroma_db`: ChromaDB database files
- `/app/backups`: Backup files

Mount these volumes to local directories for data persistence:

```bash
docker run -d -p 8000:8000 --name memory-service \
  -v /path/on/host/chroma_db:/app/chroma_db \
  -v /path/on/host/backups:/app/backups \
  mcp-memory-service
```

## Performance Considerations

### Resource Allocation

You can limit container resources using Docker's resource constraints:

```bash
docker run -d -p 8000:8000 --name memory-service \
  --memory=2g \
  --cpus=2 \
  -v ./data/chroma_db:/app/chroma_db \
  -v ./data/backups:/app/backups \
  mcp-memory-service
```

### GPU Access

To use GPU acceleration (for NVIDIA GPUs):

```bash
docker run -d -p 8000:8000 --name memory-service \
  --gpus all \
  -v ./data/chroma_db:/app/chroma_db \
  -v ./data/backups:/app/backups \
  mcp-memory-service
```

## Troubleshooting

### View Container Logs

```bash
docker logs memory-service
```

### Interactive Debugging

```bash
docker exec -it memory-service bash
```

### Common Issues

1. **Docker Boot Loop (Container Exits with Code 0)**
   
   If your container keeps restarting immediately after initialization, this is because the MCP server expects an active client connection via stdio. When no client is connected, the server exits gracefully.
   
   **Solution**: Use standalone mode:
   
   ```bash
   # Option 1: Use the standalone docker-compose file
   docker-compose -f docker-compose.standalone.yml up
   
   # Option 2: Set the environment variable
   docker run -d -p 8000:8000 --name memory-service \
     -v ./data/chroma_db:/app/chroma_db \
     -v ./data/backups:/app/backups \
     -e MCP_STANDALONE_MODE=1 \
     mcp-memory-service
   ```

2. **Permission Errors**
   
   If you see permission errors when accessing the volumes:
   
   ```bash
   # On host machine
   chmod -R 777 ./data/chroma_db ./data/backups
   ```

3. **Connection Refused**
   
   If Claude Desktop can't connect to the memory service:
   
   - Verify the container is running: `docker ps`
   - Check exposed ports: `docker port memory-service`
   - Test locally: `curl http://localhost:8000/health`

4. **Telemetry Errors**
   
   If you see ChromaDB telemetry errors during initialization, these are now automatically disabled in the Docker configuration. The errors are harmless but have been suppressed.

## Building Custom Images

You can build custom images with additional dependencies:

```dockerfile
FROM mcp-memory-service:latest

# Install additional packages
RUN python -m uv pip install pandas scikit-learn

# Copy custom configuration
COPY my_config.json /app/config.json
```

Then build and run the custom image:

```bash
docker build -t custom-memory-service -f Dockerfile.custom .
docker run -d -p 8000:8000 custom-memory-service
```
