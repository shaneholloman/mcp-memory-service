#!/bin/bash
# Install MCP Memory HTTP Service for systemd

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SERVICE_FILE="$SCRIPT_DIR/mcp-memory-http.service"
SERVICE_NAME="mcp-memory-http.service"

echo "MCP Memory HTTP Service Installation"
echo "===================================="
echo ""

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Check if .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ .env file not found: $PROJECT_DIR/.env"
    echo "Please create .env file with your configuration"
    exit 1
fi

# Check if venv exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "❌ Virtual environment not found: $PROJECT_DIR/venv"
    echo "Please run: python -m venv venv && source venv/bin/activate && pip install -e ."
    exit 1
fi

# Install as user service (recommended) or system service
echo "Installation Options:"
echo "1. User service (recommended) - runs as your user, no sudo needed"
echo "2. System service - runs at boot, requires sudo"
read -p "Select [1/2]: " choice

case $choice in
    1)
        # User service
        SERVICE_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SERVICE_DIR"

        echo "Installing user service to: $SERVICE_DIR/$SERVICE_NAME"
        cp "$SERVICE_FILE" "$SERVICE_DIR/$SERVICE_NAME"

        # Reload systemd
        systemctl --user daemon-reload

        echo ""
        echo "✅ Service installed successfully!"
        echo ""
        echo "To start the service:"
        echo "  systemctl --user start $SERVICE_NAME"
        echo ""
        echo "To enable auto-start on login:"
        echo "  systemctl --user enable $SERVICE_NAME"
        echo "  loginctl enable-linger $USER  # Required for auto-start"
        echo ""
        echo "To check status:"
        echo "  systemctl --user status $SERVICE_NAME"
        echo ""
        echo "To view logs:"
        echo "  journalctl --user -u $SERVICE_NAME -f"
        ;;

    2)
        # System service
        if [ "$EUID" -ne 0 ]; then
            echo "❌ System service installation requires sudo"
            echo "Please run: sudo $0"
            exit 1
        fi

        SERVICE_DIR="/etc/systemd/system"
        echo "Installing system service to: $SERVICE_DIR/$SERVICE_NAME"
        cp "$SERVICE_FILE" "$SERVICE_DIR/$SERVICE_NAME"

        # Reload systemd
        systemctl daemon-reload

        echo ""
        echo "✅ Service installed successfully!"
        echo ""
        echo "To start the service:"
        echo "  sudo systemctl start $SERVICE_NAME"
        echo ""
        echo "To enable auto-start on boot:"
        echo "  sudo systemctl enable $SERVICE_NAME"
        echo ""
        echo "To check status:"
        echo "  sudo systemctl status $SERVICE_NAME"
        echo ""
        echo "To view logs:"
        echo "  sudo journalctl -u $SERVICE_NAME -f"
        ;;

    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
