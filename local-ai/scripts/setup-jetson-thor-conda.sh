#!/bin/bash
# Setup Video Starter Kit Local AI on Jetson Thor
# Uses conda environments instead of Docker containers

set -e

echo "=========================================="
echo "Video Starter Kit Local AI Setup"
echo "Jetson Thor - Conda Edition"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_AI_DIR="$(dirname "$SCRIPT_DIR")"
CONDA_BASE="${CONDA_BASE:-$HOME/anaconda3}"

# Port assignments
declare -A PORTS=(
    ["gateway"]=10000
    ["comfyui"]=8188
    ["cosmos"]=10002
    ["audiocraft"]=10003
    ["tts_router"]=10004
    ["kokoro_tts"]=10005
    ["riva_tts"]=10006
)

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_cuda() {
    log_info "Checking CUDA..."
    if ! nvidia-smi &>/dev/null; then
        log_error "CUDA not available. nvidia-smi failed."
        exit 1
    fi
    log_info "CUDA OK: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
}

check_conda() {
    log_info "Checking conda..."
    if ! command -v conda &>/dev/null; then
        log_error "Conda not found. Please install Anaconda/Miniconda."
        exit 1
    fi
    log_info "Conda OK: $(conda --version)"
}

check_port() {
    local port=$1
    local service=$2
    if ss -tlnp | grep -q ":$port "; then
        log_warn "Port $port ($service) is in use"
        return 1
    fi
    return 0
}

# Create conda environments
setup_audiocraft_env() {
    log_info "Setting up vsk-audiocraft environment..."

    if conda env list | grep -q "vsk-audiocraft"; then
        log_info "vsk-audiocraft environment already exists"
    else
        log_info "Creating vsk-audiocraft environment..."
        conda create -n vsk-audiocraft python=3.10 -y
    fi

    # Install dependencies
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate vsk-audiocraft

    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130 2>/dev/null || true
    pip install transformers scipy soundfile fastapi uvicorn httpx 2>/dev/null || true

    # Verify
    python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')" || {
        log_error "Failed to verify vsk-audiocraft environment"
        exit 1
    }

    log_info "vsk-audiocraft environment ready"
}

setup_kokoro_env() {
    log_info "Setting up vsk-kokoro environment..."

    if conda env list | grep -q "vsk-kokoro"; then
        log_info "vsk-kokoro environment already exists"
    else
        log_info "Creating vsk-kokoro environment..."
        conda create -n vsk-kokoro python=3.10 -y
    fi

    # Install dependencies
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    conda activate vsk-kokoro

    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130 2>/dev/null || true
    pip install kokoro scipy soundfile fastapi uvicorn httpx 2>/dev/null || true

    # Verify
    python -c "import kokoro; print('Kokoro TTS ready')" || {
        log_error "Failed to verify vsk-kokoro environment"
        exit 1
    }

    log_info "vsk-kokoro environment ready"
}

# Install systemd services
install_systemd_services() {
    log_info "Installing systemd services..."

    local services=(
        "vsk-comfyui"
        "vsk-cosmos"
        "vsk-audiocraft"
        "vsk-kokoro-tts"
        "vsk-tts-router"
        "vsk-gateway"
    )

    for service in "${services[@]}"; do
        local service_file="$LOCAL_AI_DIR/systemd/${service}.service"
        if [[ -f "$service_file" ]]; then
            sudo cp "$service_file" /etc/systemd/system/
            log_info "Installed $service"
        else
            log_warn "Service file not found: $service_file"
        fi
    done

    sudo systemctl daemon-reload
    log_info "Systemd services installed"
}

# Enable and start services
start_services() {
    log_info "Starting services..."

    local services=(
        "vsk-audiocraft"
        "vsk-kokoro-tts"
        "vsk-tts-router"
        "vsk-gateway"
    )

    for service in "${services[@]}"; do
        sudo systemctl enable "$service" 2>/dev/null || true
        sudo systemctl start "$service" 2>/dev/null || log_warn "Could not start $service"
    done

    log_info "Services started"
}

# Stop all services
stop_services() {
    log_info "Stopping services..."

    local services=(
        "vsk-gateway"
        "vsk-tts-router"
        "vsk-kokoro-tts"
        "vsk-audiocraft"
        "vsk-cosmos"
        "vsk-comfyui"
    )

    for service in "${services[@]}"; do
        sudo systemctl stop "$service" 2>/dev/null || true
    done

    log_info "Services stopped"
}

# Check service status
check_services() {
    log_info "Checking service status..."

    echo ""
    echo "Service Status:"
    echo "==============="

    for service in vsk-comfyui vsk-cosmos vsk-audiocraft vsk-kokoro-tts vsk-tts-router vsk-gateway; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            echo -e "  $service: ${GREEN}running${NC}"
        else
            echo -e "  $service: ${RED}stopped${NC}"
        fi
    done

    echo ""
    echo "Port Status:"
    echo "============"

    for name in "${!PORTS[@]}"; do
        local port=${PORTS[$name]}
        if ss -tlnp | grep -q ":$port "; then
            echo -e "  $name ($port): ${GREEN}listening${NC}"
        else
            echo -e "  $name ($port): ${RED}not listening${NC}"
        fi
    done
}

# Health check
health_check() {
    log_info "Running health checks..."

    echo ""
    echo "Service Health:"
    echo "==============="

    # Gateway
    if curl -s http://localhost:10000/health &>/dev/null; then
        echo -e "  Gateway (10000): ${GREEN}healthy${NC}"
    else
        echo -e "  Gateway (10000): ${RED}unhealthy${NC}"
    fi

    # Audiocraft
    if curl -s http://localhost:10003/health &>/dev/null; then
        echo -e "  Audiocraft (10003): ${GREEN}healthy${NC}"
    else
        echo -e "  Audiocraft (10003): ${RED}unhealthy${NC}"
    fi

    # TTS Router
    if curl -s http://localhost:10004/health &>/dev/null; then
        echo -e "  TTS Router (10004): ${GREEN}healthy${NC}"
    else
        echo -e "  TTS Router (10004): ${RED}unhealthy${NC}"
    fi

    # Kokoro TTS
    if curl -s http://localhost:10005/health &>/dev/null; then
        echo -e "  Kokoro TTS (10005): ${GREEN}healthy${NC}"
    else
        echo -e "  Kokoro TTS (10005): ${RED}unhealthy${NC}"
    fi
}

# Main
main() {
    local cmd="${1:-setup}"

    case "$cmd" in
        setup)
            check_cuda
            check_conda
            setup_audiocraft_env
            setup_kokoro_env
            install_systemd_services
            log_info "Setup complete! Run '$0 start' to start services."
            ;;
        start)
            start_services
            sleep 5
            check_services
            ;;
        stop)
            stop_services
            ;;
        status)
            check_services
            ;;
        health)
            health_check
            ;;
        restart)
            stop_services
            sleep 2
            start_services
            sleep 5
            check_services
            ;;
        *)
            echo "Usage: $0 {setup|start|stop|restart|status|health}"
            echo ""
            echo "Commands:"
            echo "  setup   - Create conda environments and install systemd services"
            echo "  start   - Start all services"
            echo "  stop    - Stop all services"
            echo "  restart - Restart all services"
            echo "  status  - Check service status"
            echo "  health  - Run health checks"
            exit 1
            ;;
    esac
}

main "$@"
