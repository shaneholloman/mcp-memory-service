# MCP Memory Service Examples

This directory contains example configurations, scripts, and setup utilities for deploying MCP Memory Service in various scenarios.

## Directory Structure

### `/config/` - Configuration Examples
- Example Claude Desktop configurations
- Template configuration files for different deployment scenarios
- MCP server configuration samples

### `/setup/` - Setup Scripts and Utilities  
- Multi-client setup scripts
- Automated configuration tools
- Installation helpers

## Core Files

### `http-mcp-bridge.js`
A Node.js script that bridges MCP JSON-RPC protocol to HTTP REST API calls. This allows MCP clients like Claude Desktop to connect to a remote HTTP server instead of running a local instance.

**Usage:**
1. Configure your server endpoint and API key as environment variables
2. Use this script as the MCP server command in your client configuration

### `claude-desktop-http-config.json`
Example Claude Desktop configuration for connecting to a remote MCP Memory Service HTTP server via the bridge script.

**Setup:**
1. Update the path to `http-mcp-bridge.js`
2. Set your server endpoint URL
3. Add your API key (if authentication is enabled)
4. Copy this configuration to your Claude Desktop config file

## Quick Start

### 1. Server Setup
```bash
# On your server machine
cd mcp-memory-service
python install.py --server-mode --enable-http-api
export MCP_HTTP_HOST=0.0.0.0
export MCP_API_KEY="your-secure-key"
python scripts/run_http_server.py
```

### 2. Client Configuration
```bash
# Update the bridge script path and server details
cp examples/claude-desktop-http-config.json ~/.config/claude-desktop/
```

### 3. Test Connection
```bash
# Test the HTTP API directly
curl -H "Authorization: Bearer your-secure-key" \
  http://your-server:8000/api/health
```

## Advanced Usage

See the complete [Multi-Client Deployment Guide](../docs/deployment/multi-client-server.md) for detailed configuration options, security setup, and troubleshooting.