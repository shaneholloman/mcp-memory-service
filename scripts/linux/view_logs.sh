#!/bin/bash
echo "Viewing MCP Memory Service logs (press Ctrl+C to exit)..."
journalctl -u mcp-memory -f
