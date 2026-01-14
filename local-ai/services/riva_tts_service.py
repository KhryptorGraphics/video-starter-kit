#!/usr/bin/env python3
"""
Riva TTS Service - NVIDIA Riva Text-to-Speech

FastAPI wrapper for NVIDIA Riva TTS client.
Requires a Riva server to be running.

Port: 10006
Conda env: riva_thor
"""

import os
import uuid
import io
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel


# Configuration
RIVA_URL = os.getenv("RIVA_SERVER", "localhost:50051")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/tmp/riva_output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Riva client (lazy loaded)
riva_tts = None


class TTSRequest(BaseModel):
    """OpenAI-compatible TTS request."""
    model: str = "riva"
    input: str
    voice: str = "English-US.Female-1"
    response_format: str = "wav"
    speed: float = 1.0


app = FastAPI(
    title="Riva TTS Service",
    description="NVIDIA Riva Text-to-Speech",
    version="1.0.0",
)


def get_riva_client():
    """Get or create Riva TTS client."""
    global riva_tts
    if riva_tts is None:
        try:
            import riva.client
            auth = riva.client.Auth(uri=RIVA_URL)
            riva_tts = riva.client.SpeechSynthesisService(auth)
            print(f"Riva TTS connected to {RIVA_URL}")
        except Exception as e:
            print(f"Failed to connect to Riva: {e}")
            raise
    return riva_tts


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "Riva TTS",
        "riva_server": RIVA_URL,
        "status": "connected" if riva_tts is not None else "disconnected",
    }


@app.get("/health")
async def health():
    """Health check."""
    try:
        get_riva_client()
        return {"status": "healthy", "riva_server": RIVA_URL}
    except:
        return {"status": "unhealthy", "error": "Cannot connect to Riva server"}


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint."""
    return {
        "data": [
            {
                "id": "riva",
                "object": "model",
                "owned_by": "nvidia",
                "permission": [],
            }
        ]
    }


@app.get("/v1/voices")
async def list_voices():
    """List available voices."""
    # Common Riva voices
    voices = [
        {"id": "English-US.Female-1", "name": "US Female 1"},
        {"id": "English-US.Male-1", "name": "US Male 1"},
        {"id": "English-US.Female-2", "name": "US Female 2"},
        {"id": "English-US.Male-2", "name": "US Male 2"},
    ]
    return {"voices": voices}


@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """OpenAI-compatible TTS endpoint."""
    job_id = str(uuid.uuid4())

    try:
        client = get_riva_client()

        print(f"[{job_id}] Generating TTS: '{request.input[:50]}...' voice={request.voice}")

        # Generate audio
        responses = client.synthesize(
            request.input,
            voice_name=request.voice,
            language_code="en-US",
            sample_rate_hz=22050,
        )

        # Collect audio data
        audio_data = b""
        for response in responses:
            audio_data += response.audio

        # Save to file
        output_path = OUTPUT_DIR / f"{job_id}.wav"

        # Create WAV file
        import wave
        with wave.open(str(output_path), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(22050)
            wav_file.writeframes(audio_data)

        print(f"[{job_id}] Generated audio saved to {output_path}")

        return FileResponse(
            output_path,
            media_type="audio/wav",
            headers={"X-Job-ID": job_id}
        )

    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{filename}")
async def serve_file(filename: str):
    """Serve generated audio files."""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10006)
