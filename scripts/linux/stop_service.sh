#!/bin/bash
echo "Stopping MCP Memory Service..."
systemctl --user stop mcp-memory
if [ $? -eq 0 ]; then
    echo "✅ Service stopped successfully!"
else
    echo "❌ Failed to stop service"
fi
