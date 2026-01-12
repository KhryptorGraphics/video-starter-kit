"""
Local AI Gateway - Translates fal.ai API calls to local container endpoints.

This gateway provides fal.ai-compatible API endpoints that route requests
to locally running AI containers:
- ComfyUI: Image generation (Flux.1-dev)
- Cosmos: Video generation
- Audiocraft: Music generation
- Kokoro-TTS: Text-to-speech
"""

import asyncio
import uuid
import time
import os
import json
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from routes import get_route, list_available_endpoints, RouteConfig


# Job storage (in-memory for simplicity, use Redis in production)
jobs: Dict[str, Dict[str, Any]] = {}

# Generated media directory
MEDIA_DIR = Path("/data/generated")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


class GenerateRequest(BaseModel):
    """Request model matching fal.ai's format."""
    prompt: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    # Allow additional fields
    model_config = {"extra": "allow"}


class JobStatus(BaseModel):
    """Job status response."""
    request_id: str
    status: str  # "pending", "processing", "completed", "failed"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Local AI Gateway starting...")
    print(f"Available endpoints: {len(list_available_endpoints())}")
    print(f"Media directory: {MEDIA_DIR}")
    yield
    # Shutdown
    print("Local AI Gateway shutting down...")


app = FastAPI(
    title="Local AI Gateway",
    description="fal.ai-compatible gateway for local AI inference on Jetson Thor",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HTTP client for calling local containers
http_client = httpx.AsyncClient(timeout=600.0)  # 10 min timeout for inference


# =============================================================================
# ComfyUI Workflow Templates
# =============================================================================

def get_comfyui_workflow(prompt: str, width: int, height: int, steps: int = 28) -> dict:
    """Generate ComfyUI workflow JSON for Flux.1-dev."""
    return {
        "prompt": {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "cfg": 1.0,
                    "denoise": 1.0,
                    "latent_image": ["5", 0],
                    "model": ["4", 0],
                    "negative": ["7", 0],
                    "positive": ["6", 0],
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "seed": int(time.time() * 1000) % (2**32),
                    "steps": steps
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "flux1-dev.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "batch_size": 1,
                    "height": height,
                    "width": width
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": prompt
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "clip": ["4", 1],
                    "text": ""
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "flux_output",
                    "images": ["8", 0]
                }
            }
        },
        "client_id": str(uuid.uuid4())
    }


# =============================================================================
# Request/Response Transformations
# =============================================================================

def transform_request_to_local(
    endpoint_id: str,
    route: RouteConfig,
    request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Transform fal.ai request format to local container format."""

    # ComfyUI transformations
    if route.transform_request and route.transform_request.startswith("comfyui"):
        prompt = request_data.get("prompt", "")
        width = request_data.get("image_size", {}).get("width", 1024)
        height = request_data.get("image_size", {}).get("height", 1024)

        if route.transform_request == "comfyui_flux":
            return get_comfyui_workflow(prompt, width, height, steps=28)
        elif route.transform_request == "comfyui_flux_schnell":
            return get_comfyui_workflow(prompt, width, height, steps=4)
        elif route.transform_request == "comfyui_flux_ultra":
            return get_comfyui_workflow(prompt, width, height, steps=50)
        elif route.transform_request == "comfyui_sd35":
            return get_comfyui_workflow(prompt, width, height, steps=30)

    # Gradio/Audiocraft transformation
    if route.transform_request == "gradio_audiocraft":
        return {
            "data": [
                request_data.get("prompt", ""),
                request_data.get("duration", 30)
            ]
        }

    # Kokoro TTS transformation (OpenAI-compatible format)
    if route.transform_request == "kokoro_tts":
        return {
            "model": "kokoro",
            "input": request_data.get("prompt") or request_data.get("text", ""),
            "voice": request_data.get("voice", "af_heart"),
            "response_format": "wav",
            "speed": request_data.get("speed", 1.0)
        }

    # Video generation (Cosmos)
    if route.category == "video":
        return {
            "prompt": request_data.get("prompt", ""),
            "image_url": request_data.get("image_url"),
            "duration": request_data.get("duration", 5),
            "fps": request_data.get("fps", 24),
            "width": request_data.get("width", 1280),
            "height": request_data.get("height", 720),
        }

    # Default: pass through
    return dict(request_data)


def transform_response_from_local(
    route: RouteConfig,
    local_response: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """Transform local container response to fal.ai format."""

    gateway_base = os.getenv("GATEWAY_BASE_URL", "http://localhost:10000")

    if route.category == "image":
        # ComfyUI returns output info
        image_url = local_response.get("image_url")
        if not image_url and "outputs" in local_response:
            # Extract from ComfyUI response
            for node_output in local_response.get("outputs", {}).values():
                if "images" in node_output:
                    filename = node_output["images"][0].get("filename")
                    image_url = f"{gateway_base}/files/output/{filename}"
                    break

        return {
            "images": [
                {
                    "url": image_url or f"{gateway_base}/files/{job_id}.png",
                    "width": local_response.get("width", 1024),
                    "height": local_response.get("height", 1024),
                    "content_type": "image/png",
                }
            ],
            "seed": local_response.get("seed"),
            "prompt": local_response.get("prompt"),
        }

    elif route.category == "video":
        video_url = local_response.get("video_url") or local_response.get("url")
        return {
            "video": {
                "url": video_url or f"{gateway_base}/files/{job_id}.mp4",
                "content_type": "video/mp4",
            }
        }

    elif route.category in ("music", "audio"):
        # Gradio returns data array
        audio_url = local_response.get("audio_url") or local_response.get("url")
        if "data" in local_response:
            # Gradio response format
            audio_url = local_response["data"][0] if local_response["data"] else None
        return {
            "audio": {
                "url": audio_url or f"{gateway_base}/files/{job_id}.wav",
                "content_type": "audio/wav",
            }
        }

    elif route.category == "tts":
        # Kokoro returns audio directly or URL
        audio_url = local_response.get("audio_url") or local_response.get("url")
        return {
            "audio": {
                "url": audio_url or f"{gateway_base}/files/{job_id}.wav",
                "content_type": "audio/wav",
            }
        }

    # Default: pass through
    return local_response


async def process_job(
    job_id: str,
    endpoint_id: str,
    route: RouteConfig,
    request_data: Dict[str, Any]
):
    """Process a job asynchronously."""
    jobs[job_id]["status"] = "processing"
    jobs[job_id]["started_at"] = time.time()

    try:
        # Transform request
        local_request = transform_request_to_local(endpoint_id, route, request_data)

        # Call local container
        url = f"{route.local_url}{route.endpoint}"
        print(f"[{job_id}] Calling {url}")

        response = await http_client.post(url, json=local_request)
        response.raise_for_status()

        # Handle different response types
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            local_response = response.json()
        elif "audio" in content_type or "video" in content_type or "image" in content_type:
            # Binary response - save to file
            ext = "wav" if "audio" in content_type else ("mp4" if "video" in content_type else "png")
            file_path = MEDIA_DIR / f"{job_id}.{ext}"
            file_path.write_bytes(response.content)
            local_response = {"url": f"/files/{job_id}.{ext}"}
        else:
            local_response = {"raw": response.text}

        # Transform response
        fal_response = transform_response_from_local(route, local_response, job_id)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = fal_response
        jobs[job_id]["completed_at"] = time.time()
        print(f"[{job_id}] Completed in {jobs[job_id]['completed_at'] - jobs[job_id]['started_at']:.2f}s")

    except httpx.HTTPStatusError as e:
        error_msg = f"Container error: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            pass
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = error_msg
        print(f"[{job_id}] Failed: {error_msg}")

    except httpx.RequestError as e:
        error_msg = f"Connection error: {str(e)}"
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = error_msg
        print(f"[{job_id}] Failed: {error_msg}")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"[{job_id}] Failed: {str(e)}")


# =============================================================================
# API Endpoints (fal.ai compatible)
# =============================================================================

@app.get("/")
async def root():
    """Health check and info."""
    return {
        "service": "Local AI Gateway",
        "version": "2.0.0",
        "platform": "Jetson Thor (JetPack 7.4)",
        "status": "running",
        "endpoints": len(list_available_endpoints()),
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/endpoints")
async def endpoints():
    """List available endpoints."""
    return {"endpoints": list_available_endpoints()}


@app.post("/{endpoint_id:path}")
async def generate(
    endpoint_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Main generation endpoint - accepts any fal.ai endpoint ID.

    Supports both sync and async (queue) modes:
    - Sync: Returns result directly (may timeout for slow models)
    - Async: Returns request_id, poll /status/{request_id} for result
    """
    # Get route configuration
    route = get_route(endpoint_id)
    if not route:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown endpoint: {endpoint_id}. Use /endpoints to list available."
        )

    # Parse request body
    try:
        request_data = await request.json()
    except Exception:
        request_data = {}

    # Check if sync mode requested
    sync_mode = request.query_params.get("sync", "false").lower() == "true"

    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "request_id": job_id,
        "endpoint_id": endpoint_id,
        "status": "pending",
        "created_at": time.time(),
        "result": None,
        "error": None,
    }

    if sync_mode:
        # Synchronous execution
        await process_job(job_id, endpoint_id, route, request_data)
        job = jobs[job_id]

        if job["status"] == "failed":
            raise HTTPException(status_code=500, detail=job["error"])

        return job["result"]

    else:
        # Async execution (queue mode)
        background_tasks.add_task(process_job, job_id, endpoint_id, route, request_data)

        return {
            "request_id": job_id,
            "status": "pending",
            "status_url": f"/status/{job_id}",
            "result_url": f"/result/{job_id}",
        }


@app.get("/status/{request_id}")
async def get_status(request_id: str):
    """Get job status."""
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[request_id]
    return {
        "request_id": request_id,
        "status": job["status"],
    }


@app.get("/result/{request_id}")
async def get_result(request_id: str):
    """Get job result."""
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[request_id]

    if job["status"] == "pending" or job["status"] == "processing":
        return JSONResponse(
            status_code=202,
            content={"status": job["status"], "message": "Job still processing"}
        )

    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job["error"])

    return job["result"]


@app.delete("/jobs/{request_id}")
async def cancel_job(request_id: str):
    """Cancel/delete a job."""
    if request_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    del jobs[request_id]
    return {"status": "cancelled"}


# =============================================================================
# File Serving (for generated media)
# =============================================================================

@app.get("/files/{file_path:path}")
async def serve_file(file_path: str):
    """Serve generated media files."""
    # Check in generated media directory
    full_path = MEDIA_DIR / file_path
    if full_path.exists():
        return FileResponse(full_path)

    # Check in ComfyUI output directory
    comfyui_output = Path("/opt/ComfyUI/output") / file_path
    if comfyui_output.exists():
        return FileResponse(comfyui_output)

    raise HTTPException(status_code=404, detail="File not found")


# =============================================================================
# Run server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
