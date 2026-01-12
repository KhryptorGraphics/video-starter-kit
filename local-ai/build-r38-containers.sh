#!/bin/bash
# Build R38/CUDA13-compatible containers for Jetson Thor
# Run after PyTorch build completes successfully

set -e

JETSON_CONTAINERS_DIR="${HOME}/jetson-containers"
LOCAL_AI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Image tag suffix
TAG_SUFFIX="r38-local"

echo "=== R38 Container Build Script ==="
echo "Working directory: ${JETSON_CONTAINERS_DIR}"
echo ""

# Check if jetson-containers exists
if [ ! -d "${JETSON_CONTAINERS_DIR}" ]; then
    echo "Error: jetson-containers not found at ${JETSON_CONTAINERS_DIR}"
    exit 1
fi

cd "${JETSON_CONTAINERS_DIR}"

# Check if PyTorch build completed
echo "Checking for PyTorch R38 image..."
if ! docker images | grep -q "pytorch.*r38.*arm64-sbsa-cu130"; then
    echo "Warning: PyTorch R38 image not found. Build may still be in progress."
    echo "Check with: docker images | grep pytorch | grep r38"
    echo ""
    read -p "Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build containers in order (each depends on pytorch)
echo ""
echo "=== Building ComfyUI ==="
./build.sh comfyui --name "comfyui:${TAG_SUFFIX}" --skip-tests=all

echo ""
echo "=== Building Audiocraft ==="
./build.sh audiocraft --name "audiocraft:${TAG_SUFFIX}" --skip-tests=all

echo ""
echo "=== Building Kokoro TTS ==="
./build.sh kokoro-tts-fastapi --name "kokoro-tts:${TAG_SUFFIX}" --skip-tests=all

echo ""
echo "=== Building Cosmos Video Generation ==="
./build.sh cosmos1-diffusion-renderer:1.0.4 --name "cosmos:${TAG_SUFFIX}" --skip-tests=all

echo ""
echo "=== Build Complete ==="
echo ""
echo "Images built:"
docker images | grep "${TAG_SUFFIX}"

echo ""
echo "Next steps:"
echo "1. Update docker-compose.yml with new image tags:"
echo "   - comfyui:${TAG_SUFFIX}"
echo "   - cosmos:${TAG_SUFFIX}"
echo "   - audiocraft:${TAG_SUFFIX}"
echo "   - kokoro-tts:${TAG_SUFFIX}"
echo ""
echo "2. Restart the local AI stack:"
echo "   cd ${LOCAL_AI_DIR}"
echo "   docker compose down"
echo "   docker compose up -d"
echo ""
