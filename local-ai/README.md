# Local AI Setup for Video Starter Kit

Run AI inference locally on NVIDIA Jetson Thor instead of using fal.ai cloud.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Video Starter Kit                      │
│                    localhost:3000                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Local API Gateway :10000                    │
└──────┬──────────┬──────────┬──────────┬────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │ Flux   │ │ Cosmos │ │ Stable │ │  Riva  │
   │ :10001 │ │ :10002 │ │ Audio  │ │ :10004 │
   │        │ │        │ │ :10003 │ │        │
   └────────┘ └────────┘ └────────┘ └────────┘
```

## Models

| Category | Model | Container |
|----------|-------|-----------|
| Image | Flux.1-dev | dustynv/flux:dev-r36.4.0 |
| Video | NVIDIA Cosmos | nvcr.io/nim/nvidia/cosmos |
| Music | Stable Audio 2.0 | dustynv/stable-audio |
| TTS | NVIDIA Riva | nvcr.io/nvidia/riva |

## Quick Start

### 1. One-time setup

```bash
cd local-ai
./scripts/setup.sh
```

This will:
- Log into NVIDIA NGC
- Pull all container images
- Build the API gateway

### 2. Start services

```bash
./scripts/start-all.sh
```

### 3. Start the app

```bash
# In another terminal
cd ..
npm run dev
```

Open http://localhost:3000

## Configuration

### Environment Variables

Edit `.env` in this directory:

```bash
NGC_API_KEY=your-ngc-api-key
GATEWAY_PORT=10000
FLUX_PORT=10001
COSMOS_PORT=10002
STABLE_AUDIO_PORT=10003
RIVA_PORT=10004
```

### Frontend Toggle

Edit `../.env.local`:

```bash
# Enable local mode
NEXT_PUBLIC_LOCAL_AI=true

# Or disable to use fal.ai cloud
NEXT_PUBLIC_LOCAL_AI=false
```

## Commands

```bash
# Start all services
./scripts/start-all.sh

# Stop all services
./scripts/stop-all.sh

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f flux
docker compose logs -f cosmos

# Restart a specific service
docker compose restart gateway
```

## Troubleshooting

### Container won't start

Check NVIDIA runtime:
```bash
docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### GPU memory issues

Some models require significant VRAM. Try:
1. Stop other GPU processes
2. Reduce batch size in gateway config
3. Use smaller model variants

### Network issues

Ensure ports 10000-10004 are available:
```bash
lsof -i :10000
lsof -i :10001
# etc.
```

## Hardware Requirements

- NVIDIA Jetson Thor with JetPack 7.4+
- CUDA 13+
- Minimum 32GB unified memory recommended
- ~100GB disk space for model weights
