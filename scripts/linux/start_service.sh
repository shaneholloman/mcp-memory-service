#!/bin/bash
echo "Starting MCP Memory Service..."
systemctl --user start mcp-memory
if [ $? -eq 0 ]; then
    echo "✅ Service started successfully!"
else
    echo "❌ Failed to start service"
fi
