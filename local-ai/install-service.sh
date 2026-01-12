#!/bin/bash
# Install Local AI systemd service for auto-start on boot
# Run with sudo: sudo ./install-service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="local-ai"

echo "=== Local AI Service Installer ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo ./install-service.sh)"
    exit 1
fi

# Check if docker compose is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose plugin is not installed"
    exit 1
fi

# Update the service file with actual path
echo "1. Configuring service file..."
sed "s|WorkingDirectory=.*|WorkingDirectory=${SCRIPT_DIR}|" \
    "${SCRIPT_DIR}/local-ai.service" > /etc/systemd/system/${SERVICE_NAME}.service

# Install logrotate config
echo "2. Installing logrotate configuration..."
cp "${SCRIPT_DIR}/local-ai.logrotate" /etc/logrotate.d/${SERVICE_NAME}

# Reload systemd
echo "3. Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service
echo "4. Enabling service for auto-start..."
systemctl enable ${SERVICE_NAME}.service

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Commands:"
echo "  Start now:     sudo systemctl start ${SERVICE_NAME}"
echo "  Stop:          sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart:       sudo systemctl restart ${SERVICE_NAME}"
echo "  Status:        sudo systemctl status ${SERVICE_NAME}"
echo "  View logs:     sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Disable:       sudo systemctl disable ${SERVICE_NAME}"
echo ""
echo "The service will auto-start on next boot."
echo ""

# Ask if user wants to start now
read -p "Start the service now? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting ${SERVICE_NAME}..."
    systemctl start ${SERVICE_NAME}
    echo "Done! Check status with: sudo systemctl status ${SERVICE_NAME}"
fi
