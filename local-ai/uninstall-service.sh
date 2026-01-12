#!/bin/bash
# Uninstall Local AI systemd service
# Run with sudo: sudo ./uninstall-service.sh

set -e

SERVICE_NAME="local-ai"

echo "=== Local AI Service Uninstaller ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo ./uninstall-service.sh)"
    exit 1
fi

# Stop the service if running
echo "1. Stopping service..."
systemctl stop ${SERVICE_NAME}.service 2>/dev/null || true

# Disable the service
echo "2. Disabling service..."
systemctl disable ${SERVICE_NAME}.service 2>/dev/null || true

# Remove service file
echo "3. Removing service file..."
rm -f /etc/systemd/system/${SERVICE_NAME}.service

# Remove logrotate config
echo "4. Removing logrotate configuration..."
rm -f /etc/logrotate.d/${SERVICE_NAME}

# Reload systemd
echo "5. Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "=== Uninstallation Complete ==="
echo ""
echo "The Local AI service has been removed."
echo "Container data volumes are preserved. To remove them:"
echo "  docker compose down -v"
echo ""
