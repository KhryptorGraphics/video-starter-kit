#!/usr/bin/env python3
"""
Kokoro TTS Service - Text-to-Speech

FastAPI server for text-to-speech using Kokoro TTS model.
OpenAI-compatible API for easy integration.

Port: 10005
Conda env: vsk-kokoro
"""

import os
import uuid
import time
from pathlib import Path
from typing import Optional, List
import asyncio

import torch
import numpy as np
import scipy.io.wavfile as wav
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from kokoro import KPipeline


# Configuration
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/kokoro_output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_RATE = 24000

# Global pipeline (lazy loaded)
pipeline = None

# Available voices
VOICES = {
    "af_heart": "American Female (Heart)",
    "af_bella": "American Female (Bella)",
    "af_sarah": "American Female (Sarah)",
    "af_nicole": "American Female (Nicole)",
    "af_sky": "American Female (Sky)",
    "am_adam": "American Male (Adam)",
    "am_michael": "American Male (Michael)",
    "bf_emma": "British Female (Emma)",
    "bf_isabella": "British Female (Isabella)",
    "bm_george": "British Male (George)",
    "bm_lewis": "British Male (Lewis)",
}


class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request."""
    model: str = "kokoro"
    input: str
    voice: str = "af_heart"
    response_format: str = "wav"
    speed: float = 1.0


class Voice(BaseModel):
    """Voice model info."""
    id: str
    name: str


class ModelsResponse(BaseModel):
    """Available models response."""
    data: List[dict]


app = FastAPI(
    title="Kokoro TTS Service",
    description="Text-to-Speech on Jetson Thor",
    version="1.0.0",
)


def load_pipeline():
    """Load Kokoro pipeline lazily."""
    global pipeline
    if pipeline is None:
        print("Loading Kokoro TTS pipeline...")
        pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')
        print(f"Pipeline loaded, device: {DEVICE}")
    return pipeline


@app.on_event("startup")
async def startup():
    """Pre-load pipeline on startup."""
    print(f"Kokoro TTS Service starting...")
    # Load pipeline in background
    asyncio.get_event_loop().run_in_executor(None, load_pipeline)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "Kokoro TTS",
        "device": DEVICE,
        "cuda_available": torch.cuda.is_available(),
        "status": "ready" if pipeline is not None else "loading",
        "sample_rate": SAMPLE_RATE,
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "device": DEVICE}


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint."""
    return {
        "data": [
            {
                "id": "kokoro",
                "object": "model",
                "owned_by": "hexgrad",
                "permission": [],
            }
        ]
    }


@app.get("/v1/voices")
async def list_voices():
    """List available voices."""
    return {
        "voices": [
            {"id": k, "name": v} for k, v in VOICES.items()
        ]
    }


@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """OpenAI-compatible TTS endpoint."""
    pipe = load_pipeline()

    job_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        text = request.input
        voice = request.voice if request.voice in VOICES else "af_heart"

        print(f"[{job_id}] Generating TTS: '{text[:50]}...' voice={voice}")

        # Generate audio
        audio_chunks = []
        for gs, ps, audio in pipe(text, voice=voice):
            if audio is not None:
                audio_np = audio.cpu().numpy() if isinstance(audio, torch.Tensor) else audio
                audio_chunks.append(audio_np)

        # Concatenate all chunks
        if not audio_chunks:
            raise HTTPException(status_code=500, detail="No audio generated")

        full_audio = np.concatenate(audio_chunks)

        # Apply speed adjustment if needed
        if request.speed != 1.0:
            # Simple speed adjustment by resampling
            import scipy.signal as signal
            new_length = int(len(full_audio) / request.speed)
            full_audio = signal.resample(full_audio, new_length)

        duration = len(full_audio) / SAMPLE_RATE
        elapsed = time.time() - start_time

        print(f"[{job_id}] Generated {duration:.1f}s audio in {elapsed:.1f}s")

        # Save to file
        output_path = OUTPUT_DIR / f"{job_id}.wav"
        audio_int16 = (full_audio * 32767).astype(np.int16)
        wav.write(str(output_path), SAMPLE_RATE, audio_int16)

        # Return audio file
        return FileResponse(
            output_path,
            media_type="audio/wav",
            headers={"X-Job-ID": job_id, "X-Duration": str(duration)}
        )

    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate")
async def generate(prompt: str = None, text: str = None, voice: str = "af_heart"):
    """Simple generation endpoint."""
    input_text = prompt or text
    if not input_text:
        raise HTTPException(status_code=400, detail="No text provided")

    request = TTSRequest(input=input_text, voice=voice)
    return await create_speech(request)


@app.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve generated audio files."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10005)
