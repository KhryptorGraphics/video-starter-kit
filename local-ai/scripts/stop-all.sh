#!/bin/bash
# Stop all local AI services gracefully

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_AI_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Stopping Local AI Services"
echo "=========================================="

cd "$LOCAL_AI_DIR"

echo "Stopping containers gracefully..."
docker compose down

echo ""
echo "Services stopped."
echo "=========================================="
