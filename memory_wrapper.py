#!/usr/bin/env python3
"""
Wrapper script for running MCP Memory Service with Claude Code
"""
import sys
import os

# Set environment variables for Claude Code
os.environ["MCP_MEMORY_CHROMA_PATH"] = "/Users/hkr/Library/Application Support/mcp-memory/chroma_db"
os.environ["MCP_MEMORY_BACKUPS_PATH"] = "/Users/hkr/Library/Application Support/mcp-memory/backups"

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function
from mcp_memory_service.server import main

if __name__ == "__main__":
    main()
