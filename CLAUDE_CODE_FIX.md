# Fixing Claude Code Configuration for MCP Memory Service

## The Problem
Your Claude Code is configured incorrectly. It's trying to run MCP Memory Service as a Node.js project:
```
Command: node
Args: /path/to/your/mcp-memory-service/index.js
```

But MCP Memory Service is a **Python** project - there is no `index.js` file!

## Quick Fix

Run this command to reconfigure Claude Code properly:

```bash
# Remove the incorrect configuration
claude mcp remove memory

# Add the correct configuration using UV (recommended)
claude mcp add memory \
  --command "uv" \
  --args "--directory,/Users/hkr/Documents/GitHub/mcp-memory-service,run,memory"
```

## Alternative Methods

### Method 1: Using the wrapper script I just created
```bash
claude mcp add memory \
  --command "python3" \
  --args "/Users/hkr/Documents/GitHub/mcp-memory-service/memory_wrapper.py"
```

### Method 2: Using Python module directly
```bash
claude mcp add memory \
  --command "python3" \
  --args "-m,mcp_memory_service.server" \
  --env "PYTHONPATH=/Users/hkr/Documents/GitHub/mcp-memory-service/src"
```

### Method 3: Using UV with environment variables
```bash
claude mcp add memory \
  --command "uv" \
  --args "--directory,/Users/hkr/Documents/GitHub/mcp-memory-service,run,memory" \
  --env "MCP_MEMORY_CHROMA_PATH=/Users/hkr/.mcp-memory/chroma_db,MCP_MEMORY_BACKUPS_PATH=/Users/hkr/.mcp-memory/backups"
```

## Verify Your Configuration

After adding the correct configuration, check it with:
```bash
claude mcp list
```

You should see something like:
```
Memory-service MCP Server
Status: ✓ ready
Command: uv
Args: --directory,/Users/hkr/Documents/GitHub/mcp-memory-service,run,memory
```

## Prerequisites

Make sure you have:
1. **UV installed**: `pip install uv` (recommended)
2. **OR Python 3.8+**: `python3 --version`
3. **Dependencies installed**: Run the install script in the repo

## Common Issues

### If UV is not found:
```bash
# Install UV first
pip install uv

# Or use the Python method instead
```

### If you get module not found errors:
```bash
# Make sure you're in the right directory
cd /Users/hkr/Documents/GitHub/mcp-memory-service

# Install dependencies
python3 install.py
```

### If the server still won't start:
```bash
# Test it manually first
cd /Users/hkr/Documents/GitHub/mcp-memory-service
uv run memory

# Or with Python
python3 -m mcp_memory_service.server
```

## Why This Happened

This is a common confusion because:
1. Many MCP servers are written in JavaScript/TypeScript (use `node` or `npx`)
2. MCP Memory Service is written in Python (uses `python3` or `uv`)
3. The configuration format is the same, but the commands are different

## Next Steps

After fixing the configuration:
1. Restart Claude Code
2. The Memory Service should show as "✓ ready"
3. Test with a simple memory operation

## Need More Help?

- Check the docs: `/Users/hkr/Documents/GitHub/mcp-memory-service/docs/ide-compatability.md`
- Run the test: `python3 /Users/hkr/Documents/GitHub/mcp-memory-service/scripts/test_installation.py`
