#!/usr/bin/env python3
"""
TTS Router Service - Routes to Riva or Kokoro

FastAPI service that routes TTS requests to the best available backend:
1. Riva Thor (primary) - if available
2. Kokoro TTS (fallback)

Port: 10004
"""

import os
import asyncio
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# Backend URLs
RIVA_URL = os.getenv("RIVA_URL", "http://localhost:10006")  # Riva on 10006
KOKORO_URL = os.getenv("KOKORO_URL", "http://localhost:10005")  # Kokoro on 10005

# HTTP client
http_client = httpx.AsyncClient(timeout=60.0)

# Backend status
backend_status = {
    "riva": "unknown",
    "kokoro": "unknown",
    "active": None,
}


class TTSRequest(BaseModel):
    """TTS request."""
    model: str = "tts"
    input: str
    voice: str = "af_heart"
    response_format: str = "wav"
    speed: float = 1.0


app = FastAPI(
    title="TTS Router Service",
    description="Routes TTS to Riva or Kokoro",
    version="1.0.0",
)


async def check_backend(name: str, url: str, health_endpoint: str) -> bool:
    """Check if a backend is available."""
    try:
        response = await http_client.get(f"{url}{health_endpoint}", timeout=3.0)
        return response.status_code < 500
    except:
        return False


async def update_backend_status():
    """Update backend availability status."""
    global backend_status

    # Check Riva
    riva_ok = await check_backend("riva", RIVA_URL, "/health")
    backend_status["riva"] = "healthy" if riva_ok else "unavailable"

    # Check Kokoro
    kokoro_ok = await check_backend("kokoro", KOKORO_URL, "/health")
    backend_status["kokoro"] = "healthy" if kokoro_ok else "unavailable"

    # Set active backend
    if riva_ok:
        backend_status["active"] = "riva"
    elif kokoro_ok:
        backend_status["active"] = "kokoro"
    else:
        backend_status["active"] = None


@app.on_event("startup")
async def startup():
    """Initialize backend status."""
    print("TTS Router starting...")
    await update_backend_status()
    print(f"Active backend: {backend_status['active']}")


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "TTS Router",
        "backends": backend_status,
        "riva_url": RIVA_URL,
        "kokoro_url": KOKORO_URL,
    }


@app.get("/health")
async def health():
    """Health check."""
    await update_backend_status()
    return {
        "status": "healthy" if backend_status["active"] else "degraded",
        "active_backend": backend_status["active"],
        "backends": backend_status,
    }


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models endpoint."""
    return {
        "data": [
            {
                "id": "tts-router",
                "object": "model",
                "owned_by": "local",
                "permission": [],
            }
        ]
    }


@app.post("/v1/audio/speech")
async def create_speech(request: Request):
    """Route TTS request to active backend."""
    await update_backend_status()

    if not backend_status["active"]:
        raise HTTPException(status_code=503, detail="No TTS backend available")

    # Get request body
    body = await request.body()

    # Route to active backend
    if backend_status["active"] == "riva":
        target_url = f"{RIVA_URL}/v1/audio/speech"
    else:
        target_url = f"{KOKORO_URL}/v1/audio/speech"

    try:
        response = await http_client.post(
            target_url,
            content=body,
            headers={"Content-Type": "application/json"},
        )

        # Stream response back
        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "audio/wav"),
        )

    except httpx.RequestError as e:
        # Try fallback
        if backend_status["active"] == "riva" and backend_status["kokoro"] == "healthy":
            try:
                response = await http_client.post(
                    f"{KOKORO_URL}/v1/audio/speech",
                    content=body,
                    headers={"Content-Type": "application/json"},
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    media_type=response.headers.get("content-type", "audio/wav"),
                )
            except:
                pass

        raise HTTPException(status_code=503, detail=f"TTS backend error: {str(e)}")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(path: str, request: Request):
    """Proxy all other requests to active backend."""
    await update_backend_status()

    if not backend_status["active"]:
        raise HTTPException(status_code=503, detail="No TTS backend available")

    # Route to active backend
    if backend_status["active"] == "riva":
        target_url = f"{RIVA_URL}/{path}"
    else:
        target_url = f"{KOKORO_URL}/{path}"

    try:
        if request.method == "GET":
            response = await http_client.get(target_url)
        else:
            body = await request.body()
            response = await http_client.request(
                request.method,
                target_url,
                content=body,
                headers={"Content-Type": request.headers.get("content-type", "application/json")},
            )

        return Response(
            content=response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type"),
        )

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Backend error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10004)
