# Ralph Loop Orchestration: Local AI Video Starter Kit

## Mission

Complete the development and deployment of a fully local AI video generation system on NVIDIA Jetson Thor, replacing cloud-based fal.ai with local inference containers.

## Project Context

**Repository:** `/home/kp/repo2/video-starter-kit`
**Hardware:** NVIDIA Jetson Thor, JetPack 7.4, CUDA 13
**Status:** Infrastructure scaffolding complete, integration testing needed

### What's Already Built

1. **Local AI Gateway** (`local-ai/gateway/`) - FastAPI server on port 10000 that routes fal.ai-style requests to local containers
2. **Docker Compose Stack** (`local-ai/docker-compose.yml`) - Orchestrates 4 AI containers:
   - Flux.1-dev (image generation) - port 10001
   - NVIDIA Cosmos (video generation) - port 10002
   - Stable Audio 2.0 (music generation) - port 10003
   - NVIDIA Riva (TTS) - port 10004
3. **Frontend Integration** (`src/lib/fal.ts`, `src/lib/local-client.ts`) - Toggle between local/cloud mode via `NEXT_PUBLIC_LOCAL_AI=true`
4. **Setup Scripts** (`local-ai/scripts/`) - setup.sh, start-all.sh, stop-all.sh

### Key Files

```
local-ai/
├── docker-compose.yml          # Container orchestration
├── .env                        # NGC_API_KEY for pulling containers
├── gateway/
│   ├── main.py                 # FastAPI gateway (fal.ai translator)
│   ├── routes.py               # Endpoint → container mapping
│   └── Dockerfile
└── scripts/
    ├── setup.sh                # NGC login + image pulls
    ├── start-all.sh
    └── stop-all.sh

src/lib/
├── fal.ts                      # AI client (auto-switches local/cloud)
└── local-client.ts             # Local AI client implementation
```

### NGC Credentials

```
NGC_API_KEY=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
```

## Beads Task Tracking

Use beads (`bd`) to track progress. Workspace is already initialized.

### Current Tasks (Priority Order)

| ID | Priority | Title | Blocked By |
|----|----------|-------|------------|
| LOCAL-x8m | P1 | Verify and pull container images for Jetson Thor | - |
| LOCAL-ccn | P1 | Add static file serving for generated media | - |
| LOCAL-tpn | P1 | Test and fix Flux.1-dev container integration | LOCAL-x8m |
| LOCAL-7f8 | P1 | Test and fix NVIDIA Cosmos video generation | LOCAL-x8m |
| LOCAL-cvl | P1 | End-to-end testing of complete workflow | LOCAL-tpn, LOCAL-7f8 |
| LOCAL-dk7 | P2 | Test and fix Stable Audio music integration | LOCAL-x8m |
| LOCAL-3zp | P2 | Test and fix NVIDIA Riva TTS integration | LOCAL-x8m |
| LOCAL-ksu | P2 | Add health check endpoints | - |
| LOCAL-jlx | P3 | Add UI indicator for local AI mode | - |
| LOCAL-6zk | P3 | Create systemd service for auto-start | - |

### Beads Commands

```bash
# List ready tasks (no blockers)
bd ready

# Show task details
bd show LOCAL-x8m

# Update task status
bd update LOCAL-x8m --status in_progress
bd close LOCAL-x8m --reason "Completed"

# List all tasks
bd list
```

## Development Workflow

### Phase 1: Container Verification (LOCAL-x8m)

1. Research correct container images for Jetson Thor JetPack 7.4
2. Check dustynv/jetson-containers GitHub for available tags
3. Check NGC catalog for NIM containers supporting aarch64
4. Update `local-ai/docker-compose.yml` with correct images
5. Run `local-ai/scripts/setup.sh` to pull images
6. Verify all containers start: `docker compose up -d && docker compose ps`

**Research Resources:**
- https://github.com/dusty-nv/jetson-containers
- https://catalog.ngc.nvidia.com/
- NGC CLI: `ngc registry image list`

### Phase 2: Integration Testing (LOCAL-tpn, LOCAL-7f8, LOCAL-dk7, LOCAL-3zp)

For each container:
1. Start container individually: `docker compose up -d <service>`
2. Check logs: `docker compose logs -f <service>`
3. Test endpoint with curl:
   ```bash
   # Image generation
   curl -X POST http://localhost:10001/txt2img \
     -H "Content-Type: application/json" \
     -d '{"prompt": "a cat", "width": 512, "height": 512}'
   ```
4. If endpoint differs, update `local-ai/gateway/routes.py`
5. Test through gateway: `curl http://localhost:10000/fal-ai/flux/dev ...`

### Phase 3: File Serving (LOCAL-ccn)

The gateway needs to serve generated files:
1. Add `/files/<path>` route to `gateway/main.py`
2. Mount shared volume in docker-compose for media storage
3. Update response URLs to point to gateway file server

### Phase 4: End-to-End Testing (LOCAL-cvl)

1. Start all services: `./local-ai/scripts/start-all.sh`
2. Start frontend: `npm run dev`
3. Open http://localhost:3000
4. Test each generation type through the UI
5. Verify timeline composition works
6. Test video export

## Technical Notes

### Request/Response Translation

The gateway translates fal.ai API format to local container formats:

**fal.ai format:**
```json
{
  "prompt": "a beautiful sunset",
  "image_size": {"width": 1024, "height": 1024}
}
```

**Local Flux format:**
```json
{
  "prompt": "a beautiful sunset",
  "width": 1024,
  "height": 1024,
  "num_inference_steps": 28
}
```

Update `gateway/main.py` `transform_request_to_local()` function as needed.

### Container API Endpoints

Each container exposes different endpoints. Common patterns:
- dustynv containers: Usually `/generate` or `/txt2img`
- NIM containers: Usually `/v1/chat/completions` or `/generate`
- Riva: gRPC on port 50051, HTTP wrapper needed

### GPU Memory Management

Jetson Thor has unified memory. If OOM errors occur:
1. Start containers one at a time
2. Reduce batch sizes in model configs
3. Consider model quantization (INT8/FP16)

## Success Criteria

- [ ] All 4 container images pull and start on Jetson Thor
- [ ] Image generation works through gateway
- [ ] Video generation works through gateway
- [ ] Music generation works through gateway
- [ ] TTS works through gateway
- [ ] Frontend can generate all media types in local mode
- [ ] Complete video creation workflow succeeds

## Commands Reference

```bash
# Start everything
cd /home/kp/repo2/video-starter-kit
./local-ai/scripts/start-all.sh
npm run dev

# Check container status
docker compose -f local-ai/docker-compose.yml ps
docker compose -f local-ai/docker-compose.yml logs -f

# Test gateway
curl http://localhost:10000/health
curl http://localhost:10000/endpoints

# Beads task management
bd ready           # Show unblocked tasks
bd list            # Show all tasks
bd show <id>       # Task details
bd update <id> --status in_progress
bd close <id>
```
