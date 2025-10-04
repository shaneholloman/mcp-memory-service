#!/bin/bash
echo "MCP Memory Service Status:"
echo "-" | tr '-' '='
systemctl --user status mcp-memory
