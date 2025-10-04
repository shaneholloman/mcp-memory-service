#!/bin/bash
echo "This will uninstall MCP Memory Service."
read -p "Are you sure? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    exit 0
fi

echo "Stopping service..."
systemctl --user stop mcp-memory 2>/dev/null
systemctl --user disable mcp-memory 2>/dev/null

echo "Removing service files..."
if [ -f "$HOME/.config/systemd/user/mcp-memory.service" ]; then
    rm -f "$HOME/.config/systemd/user/mcp-memory.service"
    systemctl --user daemon-reload
else
    sudo rm -f /etc/systemd/system/mcp-memory.service
    sudo systemctl daemon-reload
fi

echo "✅ Service uninstalled"
