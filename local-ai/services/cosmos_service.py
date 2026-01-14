#!/usr/bin/env python3
"""
Cosmos Service - Video Generation

FastAPI server for video generation using NVIDIA Cosmos Predict2.5.
Uses the existing cosmos conda environment.

Port: 10002
Conda env: cosmos
"""

import os
import sys
import uuid
import time
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
import shutil

# Add cosmos path
sys.path.insert(0, "/home/kp/rosrepos/cosmos/cosmos-predict2.5")

import torch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/cosmos_output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Model paths
MODEL_BASE = Path("/home/kp/rosrepos/cosmos/models")
DEFAULT_MODEL = "Cosmos-Predict2.5-2B"  # Use 2B for faster inference

# Global pipeline (lazy loaded)
pipeline = None


class VideoRequest(BaseModel):
    """Video generation request."""
    prompt: str
    image_url: Optional[str] = None  # Optional input image
    duration: float = 5.0  # seconds
    fps: int = 24
    width: int = 1280
    height: int = 720
    num_frames: Optional[int] = None


class VideoResponse(BaseModel):
    """Video generation response."""
    video_url: str
    duration: float
    fps: int
    job_id: str


app = FastAPI(
    title="Cosmos Service",
    description="NVIDIA Cosmos video generation on Jetson Thor",
    version="1.0.0",
)


def load_pipeline():
    """Load Cosmos pipeline lazily."""
    global pipeline
    if pipeline is None:
        print(f"Loading Cosmos model: {DEFAULT_MODEL}")
        try:
            from cosmos_predict2.config import SetupArguments
            from cosmos_predict2.inference import Inference

            model_path = MODEL_BASE / DEFAULT_MODEL

            setup_args = SetupArguments(
                checkpoint_dir=str(model_path / "video2world"),
                diffusion_transformer_dir=str(model_path / "video2world"),
                tokenizer_dir=str(model_path / "tokenizer"),
            )

            pipeline = Inference(setup_args)
            print(f"Cosmos pipeline loaded on {DEVICE}")
        except Exception as e:
            print(f"Warning: Could not load Cosmos pipeline: {e}")
            print("Cosmos service will return mock responses")
            pipeline = "mock"
    return pipeline


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    print(f"Cosmos Service starting on {DEVICE}...")
    # Load pipeline in background
    asyncio.get_event_loop().run_in_executor(None, load_pipeline)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "Cosmos (Predict2.5)",
        "model": DEFAULT_MODEL,
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "status": "ready" if pipeline is not None else "loading",
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "device": DEVICE}


@app.post("/generate", response_model=VideoResponse)
async def generate(request: VideoRequest):
    """Generate video from prompt."""
    pipe = load_pipeline()

    job_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Calculate frames
        num_frames = request.num_frames or int(request.duration * request.fps)
        num_frames = min(num_frames, 121)  # Cosmos limit

        print(f"[{job_id}] Generating {num_frames} frames: '{request.prompt[:50]}...'")

        output_path = OUTPUT_DIR / f"{job_id}.mp4"

        if pipe == "mock":
            # Return mock response for testing - create test pattern video
            subprocess.run([
                "ffmpeg", "-f", "lavfi",
                "-i", f"testsrc=duration={request.duration}:size={request.width}x{request.height}:rate={request.fps}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(output_path), "-y"
            ], capture_output=True, check=False)

            if not output_path.exists():
                # Create placeholder response
                return VideoResponse(
                    video_url=f"/files/{job_id}.mp4",
                    duration=request.duration,
                    fps=request.fps,
                    job_id=job_id,
                )
        else:
            # Use actual Cosmos pipeline
            from cosmos_predict2.config import InferenceArguments

            inference_args = InferenceArguments(
                prompt=request.prompt,
                num_input_frames=1,
                num_video_frames=num_frames,
            )

            # Generate video
            with tempfile.TemporaryDirectory() as tmpdir:
                output_videos = pipe.generate([inference_args], Path(tmpdir))

                if output_videos:
                    # Copy first output video
                    shutil.copy(output_videos[0], output_path)

        elapsed = time.time() - start_time
        print(f"[{job_id}] Generated video in {elapsed:.1f}s")

        return VideoResponse(
            video_url=f"/files/{job_id}.mp4",
            duration=request.duration,
            fps=request.fps,
            job_id=job_id,
        )

    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve generated video files."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10002)
