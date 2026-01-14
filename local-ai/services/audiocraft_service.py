#!/usr/bin/env python3
"""
Audiocraft Service - MusicGen via Transformers

FastAPI server for music generation using Facebook's MusicGen model.
Uses Hugging Face transformers for CUDA 13 compatibility on Jetson Thor.

Port: 10003
Conda env: vsk-audiocraft
"""

import os
import uuid
import time
from pathlib import Path
from typing import Optional
import asyncio

import torch
import numpy as np
import scipy.io.wavfile as wav
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from transformers import MusicgenForConditionalGeneration, AutoProcessor


# Configuration
MODEL_NAME = os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/audiocraft_output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Global model (lazy loaded)
model = None
processor = None


class GenerateRequest(BaseModel):
    """Music generation request."""
    prompt: str
    duration: float = 10.0  # seconds
    temperature: float = 1.0
    guidance_scale: float = 3.0


class GenerateResponse(BaseModel):
    """Music generation response."""
    audio_url: str
    duration: float
    sample_rate: int
    job_id: str


app = FastAPI(
    title="Audiocraft Service",
    description="MusicGen music generation on Jetson Thor",
    version="1.0.0",
)


def load_model():
    """Load MusicGen model lazily."""
    global model, processor
    if model is None:
        print(f"Loading MusicGen model: {MODEL_NAME}")
        processor = AutoProcessor.from_pretrained(MODEL_NAME)
        model = MusicgenForConditionalGeneration.from_pretrained(MODEL_NAME)
        model = model.to(DEVICE)
        print(f"Model loaded on {DEVICE}")
    return model, processor


@app.on_event("startup")
async def startup():
    """Pre-load model on startup."""
    print(f"Audiocraft Service starting on {DEVICE}...")
    # Load model in background to not block startup
    asyncio.get_event_loop().run_in_executor(None, load_model)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "Audiocraft (MusicGen)",
        "model": MODEL_NAME,
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "status": "ready" if model is not None else "loading",
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "device": DEVICE}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate music from text prompt."""
    model, processor = load_model()

    job_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        # Calculate tokens for duration (32000 samples/sec, ~320 samples/token)
        # ~256 tokens = 5 seconds, scale accordingly
        tokens_per_second = 256 / 5.0
        max_tokens = int(request.duration * tokens_per_second)
        max_tokens = min(max_tokens, 1500)  # Cap at ~30 seconds

        print(f"[{job_id}] Generating {request.duration}s audio: '{request.prompt[:50]}...'")

        # Encode prompt
        inputs = processor(
            text=[request.prompt],
            padding=True,
            return_tensors="pt"
        ).to(DEVICE)

        # Generate audio
        with torch.no_grad():
            audio_values = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=request.temperature,
                guidance_scale=request.guidance_scale,
            )

        # Convert to numpy
        audio_np = audio_values[0, 0].cpu().numpy()
        sample_rate = model.config.audio_encoder.sampling_rate
        actual_duration = len(audio_np) / sample_rate

        # Save to file
        output_path = OUTPUT_DIR / f"{job_id}.wav"
        audio_int16 = (audio_np * 32767).astype(np.int16)
        wav.write(str(output_path), sample_rate, audio_int16)

        elapsed = time.time() - start_time
        print(f"[{job_id}] Generated {actual_duration:.1f}s audio in {elapsed:.1f}s")

        return GenerateResponse(
            audio_url=f"/files/{job_id}.wav",
            duration=actual_duration,
            sample_rate=sample_rate,
            job_id=job_id,
        )

    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predict")
async def gradio_predict(request: dict):
    """Gradio-compatible predict endpoint for gateway compatibility."""
    # Handle Gradio-style request: {"data": [prompt, duration]}
    data = request.get("data", [])
    prompt = data[0] if len(data) > 0 else ""
    duration = data[1] if len(data) > 1 else 10.0

    gen_request = GenerateRequest(prompt=prompt, duration=float(duration))
    result = await generate(gen_request)

    # Return Gradio-style response
    return {"data": [f"http://localhost:10003{result.audio_url}"]}


@app.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve generated audio files."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10003)
