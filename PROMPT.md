# Ralph Loop Orchestration: Video Starter Kit Local AI (Conda Edition)

## Mission

Complete the development and deployment of a fully local AI video generation system on NVIDIA Jetson Thor (R38/CUDA 13), using **native conda environments** instead of Docker containers. Run continuously until ALL features work and ALL tests pass.

## Project Context

**Repository:** `/home/kp/repo2/video-starter-kit`
**Hardware:** NVIDIA Jetson Thor, JetPack 7.4, L4T R38.4.0, CUDA 13.0, Driver 580.00
**Beads Workspace:** Initialized at `.beads/`
**Memory Systems:** Serena (project memories), Cipher (knowledge store)

### Critical Credentials

```
NGC_API_KEY=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
MySQL Root Password: teamrsi123teamrsi123teamrsi123
```

## Deployment Strategy: Conda Environments

**NO DOCKER CONTAINERS** for AI services. Use native conda environments with systemd services.

### Existing Conda Environments (Use These)
| Service | Environment | Python | Status |
|---------|-------------|--------|--------|
| ComfyUI | `/home/kp/anaconda3/envs/comfyui` | 3.12 | ✅ Ready |
| Cosmos | `/home/kp/anaconda3/envs/cosmos` | 3.10 | ✅ Ready |
| Riva TTS | `/home/kp/anaconda3/envs/riva_thor` | 3.11 | ✅ Ready |

### New Conda Environments (Create These)
| Service | Environment | Python | Status |
|---------|-------------|--------|--------|
| Audiocraft | `vsk-audiocraft` | 3.10 | ❌ Create |
| Kokoro TTS | `vsk-kokoro` | 3.10 | ❌ Create |

## Orchestration Rules

### Memory Layer Usage

1. **Serena**: Use for code navigation, symbol search, project memories
   - Activate project: `mcp__serena__activate_project` with `/home/kp/repo2/video-starter-kit`
   - Read/write memories for persistent knowledge
   - Use symbolic tools for code understanding

2. **Cipher**: Use for cross-session knowledge storage
   - Store research findings, API documentation
   - Query for solutions to known problems

3. **Beads**: Use for ALL task tracking
   - Create tasks morphologically as work is discovered
   - Update task status as work progresses
   - Close tasks only when verified complete
   - Track dependencies between tasks

### Port Management Protocol

Before starting ANY service:
1. Check if port is in use: `lsof -i :<port>` or `ss -tlnp | grep <port>`
2. If port in use by another project: Reconfigure THIS project to use different port
3. NEVER kill services from other projects
4. Document final port assignments in beads task notes

**Port Assignments:**
| Service | Port |
|---------|------|
| Gateway | 10000 |
| ComfyUI | 10001 |
| Cosmos | 10002 |
| Audiocraft | 10003 |
| Riva TTS | 10004 |
| Kokoro TTS | 10005 |

### Dependency Management Protocol

1. **Use existing conda environments** when available
2. **Create new project-specific envs** for missing services (vsk-*)
3. **Copy CUDA/TensorRT deps** if needed, never modify source envs
4. **Compile from source** if pip/conda unavailable - Create beads task for compilation
5. **NEVER use CPU implementations** - All CUDA/TensorRT capable code must use GPU
6. **Never modify non-project conda envs** - Only modify envs created for this project

### Morphological Task Creation

When discovering new work:
```bash
bd create --title="<descriptive title>" --type=task|bug|feature --priority=<0-4>
bd dep add <new-task> <blocking-task>  # If dependencies exist
```

When a task reveals sub-tasks, create them and link dependencies.

---

## Phase 1: Environment Setup

### 1a. Create Audiocraft Environment

```bash
# Create new conda environment
conda create -n vsk-audiocraft python=3.10 -y
conda activate vsk-audiocraft

# Install PyTorch with CUDA 13 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130

# Install audiocraft (compile from source if needed)
pip install git+https://github.com/facebookresearch/audiocraft.git

# Verify GPU access
python -c "import torch; print(torch.cuda.is_available())"
```

If installation fails, create beads task and compile from source.

### 1b. Create Kokoro TTS Environment

```bash
# Create Kokoro TTS environment
conda create -n vsk-kokoro python=3.10 -y
conda activate vsk-kokoro

# Install PyTorch with CUDA 13
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu130

# Install Kokoro TTS
pip install git+https://github.com/hexgrad/kokoro.git

# Or if that fails, clone and build:
git clone https://github.com/hexgrad/kokoro.git /tmp/kokoro
cd /tmp/kokoro && pip install -e .

# Verify
python -c "import kokoro; print('Kokoro installed')"
```

---

## Phase 2: Service Wrappers

Create FastAPI servers in `local-ai/services/`:

### ComfyUI Service (`comfyui_service.py`)
- Wrap existing ComfyUI installation
- Expose API on port 10001
- Handle workflow submission and result retrieval

### Cosmos Service (`cosmos_service.py`)
- Wrap existing Cosmos installation
- Expose API on port 10002
- Handle text-to-video and image-to-video

### Audiocraft Service (`audiocraft_service.py`)
- NEW service for MusicGen
- Expose API on port 10003
- Handle music generation from text prompts

### TTS Services
- `riva_tts_service.py` - Wrap Riva Thor (port 10004)
- `kokoro_tts_service.py` - Wrap Kokoro (port 10005)
- `tts_router.py` - Route to available TTS service

---

## Phase 3: Systemd Services

Create systemd unit files in `local-ai/systemd/`:

### Template for each service:
```ini
[Unit]
Description=VSK <Service Name>
After=network.target

[Service]
Type=simple
User=kp
WorkingDirectory=/home/kp/repo2/video-starter-kit/local-ai
Environment="PATH=/home/kp/anaconda3/envs/<env>/bin:$PATH"
ExecStart=/home/kp/anaconda3/envs/<env>/bin/python services/<service>.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Installation:
```bash
sudo cp local-ai/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vsk-comfyui vsk-cosmos vsk-audiocraft vsk-riva-tts vsk-kokoro-tts vsk-gateway
sudo systemctl start vsk-comfyui vsk-cosmos vsk-audiocraft vsk-riva-tts vsk-kokoro-tts vsk-gateway
```

---

## Phase 4: Gateway Updates

Update `local-ai/gateway/`:

1. **main.py**: Update service URLs to localhost ports
2. **routes.py**:
   - Route `/fal-ai/flux/*` to ComfyUI (10001)
   - Route `/fal-ai/cosmos/*` to Cosmos (10002)
   - Route `/fal-ai/audio/*` to Audiocraft (10003)
   - Route `/fal-ai/tts/*` to TTS router (checks Riva then Kokoro)
3. **Health checks**: Add endpoints to verify all services

---

## Phase 5: Testing

### Individual Service Tests

```bash
# ComfyUI
curl -X POST http://localhost:10001/api/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": {...}}'

# Cosmos
curl -X POST http://localhost:10002/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a cat walking", "num_frames": 16}'

# Audiocraft
curl -X POST http://localhost:10003/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "upbeat electronic music", "duration": 10}'

# Riva TTS
curl -X POST http://localhost:10004/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "English-US.Female-1"}'

# Kokoro TTS
curl -X POST http://localhost:10005/v1/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world"}'

# Gateway health
curl http://localhost:10000/health
```

### GPU Verification
```bash
nvidia-smi  # All services should show GPU processes
```

---

## Phase 6: Browser Automation Testing

Use Skyvern or Playwright for E2E testing:

### Test Workflow:
1. Navigate to http://localhost:3000
2. Test image generation (Flux)
3. Test video generation (Cosmos)
4. Test music generation (Audiocraft)
5. Test TTS (Riva/Kokoro)
6. Test timeline composition
7. Test video export

Create beads tasks for any failures found.

---

## Phase 7: Setup Scripts

Create `local-ai/scripts/setup-jetson-thor-conda.sh`:

```bash
#!/bin/bash
# Setup Video Starter Kit Local AI on Jetson Thor

# Check prerequisites
check_cuda() { nvidia-smi &>/dev/null || { echo "CUDA not found"; exit 1; } }
check_conda() { conda --version &>/dev/null || { echo "Conda not found"; exit 1; } }

# Check port availability
check_port() {
    if ss -tlnp | grep -q ":$1 "; then
        echo "Port $1 in use, finding alternative..."
        # Find next available port
    fi
}

# Create missing environments
setup_audiocraft() { ... }
setup_kokoro() { ... }

# Install systemd services
install_services() { ... }

# Start all services
start_services() { ... }

# Main
check_cuda
check_conda
check_port 10000
check_port 10001
# ... etc
setup_audiocraft
setup_kokoro
install_services
start_services
echo "Setup complete!"
```

---

## Success Criteria

All must be true before project is complete:

- [ ] Audiocraft conda env created with CUDA 13 support
- [ ] Kokoro TTS conda env created with CUDA 13 support
- [ ] All AI services running as systemd units
- [ ] Gateway health check passes: `curl http://localhost:10000/health`
- [ ] Image generation works (ComfyUI/Flux)
- [ ] Video generation works (Cosmos)
- [ ] Music generation works (Audiocraft)
- [ ] TTS works (Riva Thor OR Kokoro)
- [ ] Frontend works with `NEXT_PUBLIC_LOCAL_AI=true`
- [ ] Complete video creation workflow succeeds
- [ ] Browser automation tests pass
- [ ] Setup scripts work on fresh Jetson Thor environment
- [ ] All beads tasks are closed

---

## Fix Loop Protocol

When problems are found:

1. **Research**: Use web search, Perplexity, or Linkup to find solutions
2. **Plan**: Create beads task with description and acceptance criteria
3. **Implement**: Make code changes
4. **Test**: Verify fix works
5. **Iterate**: If still broken, research more and try again

```
LOOP until all tests pass:
  1. Run all tests
  2. If failure found:
     a. Create beads task for fix
     b. Research solution (use scholarly MCP servers for cutting-edge issues)
     c. Implement fix
     d. Test fix
     e. If fixed: Close task
     f. If not fixed: Update task notes, continue research
  3. If all tests pass: Move to next phase
```

---

## Commands Reference

```bash
# Conda
conda activate vsk-audiocraft
conda activate vsk-kokoro
conda activate comfyui
conda activate cosmos
conda activate riva_thor

# Beads
bd ready                    # Show unblocked tasks
bd list --status=open       # All open tasks
bd show <id>                # Task details
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd create --title="..." --type=task --priority=2

# Systemd
sudo systemctl status vsk-*
sudo systemctl start vsk-comfyui
sudo systemctl stop vsk-comfyui
sudo systemctl restart vsk-*
journalctl -u vsk-comfyui -f  # View logs

# Port checking
lsof -i :10000
ss -tlnp | grep 10000

# GPU monitoring
nvidia-smi
watch -n 1 nvidia-smi
```

---

## Continuous Operation

Ralph Loop should:
1. Check `bd ready` for available work
2. Pick highest priority unblocked task
3. Work on task until complete or blocked
4. Update beads with progress
5. If blocked, create new tasks for blockers
6. Repeat until all success criteria met
7. NEVER stop until project is 100% complete and verified
