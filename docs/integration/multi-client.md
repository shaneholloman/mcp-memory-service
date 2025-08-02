# Multi-Client Setup Guide

This comprehensive guide covers setting up MCP Memory Service for multiple clients, enabling shared memory access across different applications and devices.

## Overview

MCP Memory Service supports multi-client access through several deployment patterns:

1. **🌟 Integrated Setup** (Easiest - during installation)
2. **📁 Shared File Access** (Local networks with shared storage)
3. **🌐 Centralized HTTP/SSE Server** (Distributed teams and cloud deployment)

## 🌟 Integrated Setup (Recommended)

### During Installation

The easiest way to configure multi-client access is during the initial installation:

```bash
# Run the installer - you'll be prompted for multi-client setup
python install.py

# When prompted, choose 'y':
# 🌐 Multi-Client Access Available!
# Would you like to configure multi-client access? (y/N): y
```

**Benefits of integrated setup:**
- ✅ Automatic detection of Claude Desktop, VS Code, Continue, Cursor, and other MCP clients
- ✅ Universal compatibility beyond just Claude applications
- ✅ Zero manual configuration required
- ✅ Future-proof setup for any MCP application

### Command Line Options

```bash
# Automatic multi-client setup (no prompts)
python install.py --setup-multi-client

# Skip the multi-client prompt entirely
python install.py --skip-multi-client-prompt

# Combined with other options
python install.py --storage-backend sqlite_vec --setup-multi-client
```

### Supported Applications

The integrated setup automatically detects and configures:

#### Automatically Configured
- **Claude Desktop**: Updates `claude_desktop_config.json` with multi-client settings
- **Continue IDE**: Modifies Continue configuration files
- **VS Code MCP Extension**: Updates VS Code MCP settings
- **Cursor**: Configures Cursor MCP integration
- **Generic MCP Clients**: Updates `.mcp.json` and similar configuration files

#### Manual Configuration Required
- **Custom MCP implementations**: May require manual configuration file updates
- **Enterprise MCP clients**: Check with your IT department for configuration requirements

## 📁 Shared File Access (Local Networks)

### Overview

For local networks with shared storage, multiple clients can access the same SQLite database using Write-Ahead Logging (WAL) mode.

### Quick Setup

1. **Run the setup script:**
   ```bash
   python setup_multi_client_complete.py
   ```

2. **Configure shared database location:**
   ```bash
   export MCP_MEMORY_SQLITE_VEC_PATH="/shared/network/mcp_memory"
   export MCP_MEMORY_ENABLE_WAL=true
   ```

3. **Update each client configuration** to point to the shared location.

### Technical Implementation

The shared file access uses SQLite's WAL (Write-Ahead Logging) mode for concurrent access:

- **WAL Mode**: Enables multiple readers and one writer simultaneously
- **File Locking**: Handles concurrent access safely
- **Automatic Recovery**: SQLite handles crash recovery automatically

### Configuration Example

For Claude Desktop on each client machine:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["/path/to/mcp-memory-service/src/mcp_memory_service/server.py"],
      "env": {
        "MCP_MEMORY_SQLITE_VEC_PATH": "/shared/network/mcp_memory",
        "MCP_MEMORY_ENABLE_WAL": "true",
        "MCP_MEMORY_STORAGE_BACKEND": "sqlite_vec"
      }
    }
  }
}
```

### Network Storage Requirements

- **NFS/SMB Share**: Properly configured network file system
- **File Permissions**: Read/write access for all client users
- **Network Reliability**: Stable network connection to prevent corruption

## 🌐 Centralized HTTP/SSE Server (Cloud Deployment)

### Why This Approach?

- ✅ **True Concurrency**: Proper handling of multiple simultaneous clients
- ✅ **Real-time Updates**: Server-Sent Events (SSE) push changes to all clients instantly
- ✅ **Cross-platform**: Works from any device with HTTP access
- ✅ **Secure**: Optional API key authentication
- ✅ **Scalable**: Can handle many concurrent clients
- ✅ **Cloud-friendly**: No file locking issues

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client PC 1   │    │   Client PC 2   │    │   Client PC 3   │
│   (Claude App)  │    │   (VS Code)     │    │   (Web Client)  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │         HTTP/SSE API │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼──────────────┐
                    │     Central Server         │
                    │  ┌─────────────────────┐   │
                    │  │ MCP Memory Service  │   │
                    │  │   HTTP/SSE Server   │   │
                    │  └─────────────────────┘   │
                    │  ┌─────────────────────┐   │
                    │  │   SQLite-vec DB     │   │
                    │  │   (Single Source)   │   │
                    │  └─────────────────────┘   │
                    └────────────────────────────┘
```

### Server Installation

1. **Install on your server machine:**
   ```bash
   git clone https://github.com/doobidoo/mcp-memory-service.git
   cd mcp-memory-service
   python install.py --server-mode --storage-backend sqlite_vec
   ```

2. **Configure HTTP server:**
   ```bash
   export MCP_MEMORY_HTTP_HOST=0.0.0.0
   export MCP_MEMORY_HTTP_PORT=8000
   export MCP_MEMORY_API_KEY=your-secure-api-key
   ```

3. **Start the HTTP server:**
   ```bash
   python scripts/run_http_server.py
   ```

### Client Configuration (HTTP Mode)

Each client connects to the centralized server via HTTP:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["/path/to/mcp-memory-service/scripts/http_client.py"],
      "env": {
        "MCP_MEMORY_HTTP_URL": "http://your-server:8000",
        "MCP_MEMORY_API_KEY": "your-secure-api-key",
        "MCP_MEMORY_ENABLE_SSE": "true"
      }
    }
  }
}
```

### Security Configuration

#### API Key Authentication

```bash
# Generate a secure API key
export MCP_MEMORY_API_KEY=$(openssl rand -hex 32)

# Configure HTTPS (recommended for production)
export MCP_MEMORY_USE_HTTPS=true
export MCP_MEMORY_SSL_CERT=/path/to/cert.pem
export MCP_MEMORY_SSL_KEY=/path/to/key.pem
```

#### Firewall Configuration

```bash
# Allow HTTP/HTTPS access (adjust port as needed)
sudo ufw allow 8000/tcp
sudo ufw allow 8443/tcp  # For HTTPS
```

### Docker Deployment

For containerized deployment:

```yaml
# docker-compose.yml
version: '3.8'
services:
  mcp-memory-service:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MCP_MEMORY_HTTP_HOST=0.0.0.0
      - MCP_MEMORY_HTTP_PORT=8000
      - MCP_MEMORY_API_KEY=${MCP_MEMORY_API_KEY}
      - MCP_MEMORY_STORAGE_BACKEND=sqlite_vec
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

```bash
# Deploy with Docker Compose
docker-compose up -d
```

## Advanced Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_MEMORY_MULTI_CLIENT` | `false` | Enable multi-client mode |
| `MCP_MEMORY_ENABLE_WAL` | `false` | Enable SQLite WAL mode |
| `MCP_MEMORY_HTTP_HOST` | `127.0.0.1` | HTTP server bind address |
| `MCP_MEMORY_HTTP_PORT` | `8000` | HTTP server port |
| `MCP_MEMORY_API_KEY` | `none` | API key for authentication |
| `MCP_MEMORY_ENABLE_SSE` | `true` | Enable Server-Sent Events |
| `MCP_MEMORY_MAX_CLIENTS` | `50` | Maximum concurrent clients |

### Performance Tuning

#### SQLite Configuration

```bash
# Optimize for concurrent access
export MCP_MEMORY_SQLITE_BUSY_TIMEOUT=5000
export MCP_MEMORY_SQLITE_CACHE_SIZE=10000
export MCP_MEMORY_SQLITE_JOURNAL_MODE=WAL
```

#### HTTP Server Tuning

```bash
# Adjust for high concurrency
export MCP_MEMORY_HTTP_WORKERS=4
export MCP_MEMORY_HTTP_TIMEOUT=30
export MCP_MEMORY_HTTP_KEEPALIVE=true
```

## Troubleshooting

### Common Issues

#### 1. Database Lock Errors

**Symptom**: `database is locked` errors
**Solution**: Enable WAL mode and check file permissions:

```bash
export MCP_MEMORY_ENABLE_WAL=true
chmod 666 /path/to/memory.db
chmod 777 /path/to/memory.db-wal
```

#### 2. Network Access Issues

**Symptom**: Clients can't connect to HTTP server
**Solution**: Check firewall and network connectivity:

```bash
# Test server connectivity
curl http://your-server:8000/health

# Check firewall rules
sudo ufw status
```

#### 3. Configuration Conflicts

**Symptom**: Clients use different configurations
**Solution**: Verify all clients use the same settings:

```bash
# Check environment variables on each client
env | grep MCP_MEMORY

# Verify database paths match
ls -la $MCP_MEMORY_SQLITE_VEC_PATH
```

### Diagnostic Commands

#### Check Multi-Client Status

```bash
# Test multi-client setup
python scripts/test_multi_client.py

# Verify database access
python -c "
import sqlite3
conn = sqlite3.connect('$MCP_MEMORY_SQLITE_VEC_PATH/memory.db')
print(f'Database accessible: {conn is not None}')
conn.close()
"
```

#### Monitor Client Connections

```bash
# For HTTP server deployment
curl http://your-server:8000/stats

# Check active connections
netstat -an | grep :8000
```

## Migration from Single-Client

### Upgrading Existing Installation

1. **Backup existing data:**
   ```bash
   python scripts/backup_memories.py
   ```

2. **Run multi-client setup:**
   ```bash
   python install.py --setup-multi-client --migrate-existing
   ```

3. **Update client configurations** as needed.

### Data Migration

The installer automatically handles data migration, but you can also run it manually:

```bash
# Migrate to shared database location
python scripts/migrate_to_multi_client.py \
  --source ~/.mcp_memory_chroma \
  --target /shared/mcp_memory
```

## Related Documentation

- [Installation Guide](../installation/master-guide.md) - General installation instructions
- [Deployment Guide](../deployment/docker.md) - Docker and cloud deployment
- [Troubleshooting](../troubleshooting/general.md) - Multi-client specific issues
- [API Reference](../IMPLEMENTATION_PLAN_HTTP_SSE.md) - HTTP/SSE API documentation