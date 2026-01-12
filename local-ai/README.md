# Local AI Setup for Video Starter Kit

Run AI inference locally on NVIDIA Jetson instead of using fal.ai cloud.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Video Starter Kit                          │
│                    localhost:3000                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ NEXT_PUBLIC_LOCAL_AI=true
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Local AI Gateway                           │
│                    (Port 10000)                              │
│  - fal.ai API compatibility layer                           │
│  - Job queue management                                      │
│  - Request routing to backends                               │
└───────┬─────────┬─────────┬─────────┬───────────────────────┘
        │         │         │         │
        ▼         ▼         ▼         ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ComfyUI │ │ Cosmos │ │Audio-  │ │Kokoro  │
   │ :10001 │ │ :10002 │ │craft   │ │TTS     │
   │        │ │        │ │ :10003 │ │ :10004 │
   │Flux.1  │ │Video   │ │MusicGen│ │Speech  │
   └────────┘ └────────┘ └────────┘ └────────┘
```

## Services

| Service | Port | Model | Purpose |
|---------|------|-------|---------|
| Gateway | 10000 | - | API routing & job management |
| ComfyUI | 10001 | Flux.1-dev | Image generation |
| Cosmos | 10002 | Cosmos-1.0 | Video generation |
| Audiocraft | 10003 | MusicGen | Music generation |
| Kokoro TTS | 10004 | Kokoro | Text-to-speech |

## Quick Start

### 1. Start services

```bash
cd local-ai
docker compose up -d
```

### 2. Check health

```bash
./check-health.sh
```

### 3. Enable local AI in the app

```bash
# In the main project directory
export NEXT_PUBLIC_LOCAL_AI=true
export NEXT_PUBLIC_LOCAL_AI_URL=http://localhost:10000
npm run dev
```

Open http://localhost:3000 - you should see a green "Local AI" badge in the header.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_LOCAL_AI` | `false` | Enable local AI mode |
| `NEXT_PUBLIC_LOCAL_AI_URL` | `http://localhost:10000` | Gateway URL |
| `GATEWAY_PORT` | `10000` | Gateway external port |
| `COMFYUI_PORT` | `10001` | ComfyUI external port |
| `COSMOS_PORT` | `10002` | Cosmos external port |
| `AUDIOCRAFT_PORT` | `10003` | Audiocraft external port |
| `TTS_PORT` | `10004` | TTS external port |

### Docker Compose Override

Create a `.env` file to customize:

```bash
GATEWAY_PORT=10000
COMFYUI_PORT=10001
COSMOS_PORT=10002
AUDIOCRAFT_PORT=10003
TTS_PORT=10004
```

## Auto-Start on Boot

Install as a systemd service for automatic startup:

```bash
sudo ./install-service.sh
```

Commands:
```bash
sudo systemctl start local-ai     # Start services
sudo systemctl stop local-ai      # Stop services
sudo systemctl status local-ai    # Check status
sudo journalctl -u local-ai -f    # View logs
```

To uninstall:
```bash
sudo ./uninstall-service.sh
```

## Health Monitoring

### CLI
```bash
./check-health.sh           # Basic check
./check-health.sh --verbose # Detailed JSON output
```

### API
- `GET /health` - Basic gateway status
- `GET /health/detailed` - All backend services status

### Docker
```bash
docker compose ps              # Container status
docker compose logs -f         # All logs
docker compose logs -f cosmos  # Specific service
```

## Troubleshooting

### CUDA Error 801: operation not supported

**Cause:** Container built for different CUDA/L4T version than host.

**Solution:** Build containers matching your system using [jetson-containers](https://github.com/dusty-nv/jetson-containers):

```bash
git clone https://github.com/dusty-nv/jetson-containers
cd jetson-containers

# Check your L4T version
cat /etc/nv_tegra_release

# Build PyTorch for your version
./build.sh pytorch

# Build app containers
./build.sh comfyui audiocraft
```

### Container won't start

```bash
# Check logs
docker compose logs [service]

# Verify GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# Check NVIDIA runtime
docker info | grep -i runtime
```

### Out of memory

The Jetson Thor has unified memory shared between CPU and GPU. If you run out:

1. Stop unused services: `docker compose stop cosmos`
2. Use smaller models
3. Reduce batch size in gateway config
4. Close other GPU applications

### Port conflicts

```bash
# Check what's using a port
lsof -i :10000

# Kill process
kill -9 $(lsof -t -i:10000)
```

## Hardware Requirements

- **Recommended:** NVIDIA Jetson Thor with JetPack 7.4+
- **Minimum:** Jetson Orin 32GB
- CUDA 13.0+ (for R38.x containers)
- ~60GB disk space for containers
- ~100GB additional for model weights

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Container orchestration |
| `gateway/` | FastAPI gateway service |
| `audiocraft_server.py` | Gradio wrapper for MusicGen |
| `check-health.sh` | Health check CLI script |
| `local-ai.service` | systemd unit file |
| `local-ai.logrotate` | Log rotation config |
| `install-service.sh` | Service installer |
| `uninstall-service.sh` | Service uninstaller |

## API Compatibility

The gateway provides fal.ai-compatible endpoints:

```
POST /{endpoint_id}         # Submit job
GET  /status/{request_id}   # Check status
GET  /result/{request_id}   # Get result
GET  /health                # Health check
GET  /health/detailed       # Detailed status
```

This allows the Video Starter Kit frontend to work without modification - just set `NEXT_PUBLIC_LOCAL_AI=true`.
