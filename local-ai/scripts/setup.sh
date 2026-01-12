#!/bin/bash
# One-time setup script for local AI containers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_AI_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Local AI Setup for Video Starter Kit"
echo "=========================================="

# Load environment variables
if [ -f "$LOCAL_AI_DIR/.env" ]; then
    source "$LOCAL_AI_DIR/.env"
else
    echo "ERROR: .env file not found at $LOCAL_AI_DIR/.env"
    exit 1
fi

# Check NGC API key
if [ -z "$NGC_API_KEY" ]; then
    echo "ERROR: NGC_API_KEY not set in .env"
    exit 1
fi

echo ""
echo "[1/4] Logging into NVIDIA NGC..."
echo "$NGC_API_KEY" | docker login nvcr.io -u '$oauthtoken' --password-stdin

echo ""
echo "[2/4] Pulling container images (this may take a while)..."

echo "  -> Pulling Flux.1-dev..."
docker pull dustynv/flux:dev-r36.4.0 || echo "  [!] Flux image not available, will try alternative"

echo "  -> Pulling NVIDIA Cosmos..."
docker pull nvcr.io/nim/nvidia/cosmos-1.0-diffusion-7b-text2world:1.0.0 || echo "  [!] Cosmos pull failed, check NGC access"

echo "  -> Pulling Stable Audio..."
docker pull dustynv/stable-audio:r36.4.0 || echo "  [!] Stable Audio not available, will try alternative"

echo "  -> Pulling NVIDIA Riva..."
docker pull nvcr.io/nvidia/riva/riva-speech:2.16.0-l4t-aarch64 || echo "  [!] Riva pull failed, check NGC access"

echo ""
echo "[3/4] Building API Gateway..."
cd "$LOCAL_AI_DIR"
docker compose build gateway

echo ""
echo "[4/4] Creating cache volumes..."
docker volume create flux-cache 2>/dev/null || true
docker volume create cosmos-cache 2>/dev/null || true
docker volume create audio-cache 2>/dev/null || true
docker volume create riva-cache 2>/dev/null || true

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run: ./scripts/start-all.sh"
echo "  2. In another terminal: npm run dev"
echo "  3. Open http://localhost:3000"
echo "=========================================="
