#!/bin/bash
# Wrapper script for Claude Code to run MCP Memory Service with proper environment variables

export MCP_MEMORY_CHROMA_PATH="/Users/hkr/Library/Application Support/mcp-memory/chroma_db"
export MCP_MEMORY_BACKUPS_PATH="/Users/hkr/Library/Application Support/mcp-memory/backups"

# Run the memory service using uv
cd /Users/hkr/Documents/GitHub/mcp-memory-service
uv run memory
