#!/bin/bash
# Start all local AI services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_AI_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Starting Local AI Services"
echo "=========================================="

cd "$LOCAL_AI_DIR"

# Check if containers are already running
if docker compose ps --quiet 2>/dev/null | grep -q .; then
    echo "Some services already running. Stopping first..."
    docker compose down
fi

echo ""
echo "Starting all services..."
docker compose up -d

echo ""
echo "Waiting for services to initialize..."
sleep 10

echo ""
echo "Service Status:"
echo "----------------------------------------"
docker compose ps

echo ""
echo "=========================================="
echo "Local AI Services Started!"
echo ""
echo "Endpoints:"
echo "  Gateway:      http://localhost:10000"
echo "  Flux (Image): http://localhost:10001"
echo "  Cosmos (Vid): http://localhost:10002"
echo "  Audio:        http://localhost:10003"
echo "  Riva (TTS):   http://localhost:10004"
echo ""
echo "View logs: docker compose logs -f"
echo "=========================================="
