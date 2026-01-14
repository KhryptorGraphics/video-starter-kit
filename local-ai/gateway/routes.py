"""
Route mapping from fal.ai endpoints to local containers.

Container APIs:
- ComfyUI (port 8188): HTTP API at /prompt for workflow execution
- Cosmos (port 8000): Video generation via /generate
- Audiocraft (port 8000): Gradio API for music generation
- Kokoro-TTS (port 8880): FastAPI at /v1/audio/speech
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

# Service URLs from environment
# ComfyUI runs on 8188 (its native port, exposed via systemd)
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
# Cosmos video generation service
COSMOS_URL = os.getenv("COSMOS_URL", "http://localhost:10002")
# Audiocraft music generation service
AUDIOCRAFT_URL = os.getenv("AUDIOCRAFT_URL", "http://localhost:10003")
# TTS router (routes to Riva or Kokoro)
TTS_URL = os.getenv("TTS_URL", "http://localhost:10004")


@dataclass
class RouteConfig:
    """Configuration for a route mapping."""
    local_url: str
    endpoint: str = "/generate"
    category: str = "image"
    transform_request: Optional[str] = None
    transform_response: Optional[str] = None


# Map fal.ai endpoint IDs to local services
ROUTE_MAP: Dict[str, RouteConfig] = {
    # =========================================================================
    # Image Generation - ComfyUI with Flux.1-dev
    # ComfyUI uses /prompt endpoint with workflow JSON
    # =========================================================================
    "fal-ai/flux/dev": RouteConfig(
        local_url=COMFYUI_URL,
        endpoint="/prompt",
        category="image",
        transform_request="comfyui_flux",
    ),
    "fal-ai/flux/schnell": RouteConfig(
        local_url=COMFYUI_URL,
        endpoint="/prompt",
        category="image",
        transform_request="comfyui_flux_schnell",
    ),
    "fal-ai/flux-pro/v1.1-ultra": RouteConfig(
        local_url=COMFYUI_URL,
        endpoint="/prompt",
        category="image",
        transform_request="comfyui_flux_ultra",
    ),
    "fal-ai/stable-diffusion-v35-large": RouteConfig(
        local_url=COMFYUI_URL,
        endpoint="/prompt",
        category="image",
        transform_request="comfyui_sd35",
    ),

    # =========================================================================
    # Video Generation - NVIDIA Cosmos
    # =========================================================================
    "fal-ai/minimax/video-01-live": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),
    "fal-ai/hunyuan-video": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),
    "fal-ai/kling-video/v1.5/pro": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),
    "fal-ai/kling-video/v1/standard/text-to-video": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),
    "fal-ai/luma-dream-machine": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),
    "fal-ai/veo2": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),
    "fal-ai/ltx-video-v095/multiconditioning": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/generate",
        category="video",
    ),

    # =========================================================================
    # Audio/Music Generation - Meta's Audiocraft (MusicGen)
    # Uses Gradio API
    # =========================================================================
    "fal-ai/minimax-music": RouteConfig(
        local_url=AUDIOCRAFT_URL,
        endpoint="/api/predict",
        category="music",
        transform_request="gradio_audiocraft",
    ),
    "fal-ai/stable-audio": RouteConfig(
        local_url=AUDIOCRAFT_URL,
        endpoint="/api/predict",
        category="music",
        transform_request="gradio_audiocraft",
    ),
    "fal-ai/mmaudio-v2": RouteConfig(
        local_url=AUDIOCRAFT_URL,
        endpoint="/api/predict",
        category="audio",
        transform_request="gradio_audiocraft",
    ),

    # =========================================================================
    # Text-to-Speech - Kokoro TTS
    # OpenAI-compatible API at /v1/audio/speech
    # =========================================================================
    "fal-ai/playht/tts/v3": RouteConfig(
        local_url=TTS_URL,
        endpoint="/v1/audio/speech",
        category="tts",
        transform_request="kokoro_tts",
    ),
    "fal-ai/playai/tts/dialog": RouteConfig(
        local_url=TTS_URL,
        endpoint="/v1/audio/speech",
        category="tts",
        transform_request="kokoro_tts",
    ),
    "fal-ai/f5-tts": RouteConfig(
        local_url=TTS_URL,
        endpoint="/v1/audio/speech",
        category="tts",
        transform_request="kokoro_tts",
    ),

    # =========================================================================
    # Post-processing - Route to Cosmos or ComfyUI
    # =========================================================================
    "fal-ai/sync-lipsync": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/lipsync",
        category="video",
    ),
    "fal-ai/topaz/upscale/video": RouteConfig(
        local_url=COSMOS_URL,
        endpoint="/upscale",
        category="video",
    ),
}


def get_route(endpoint_id: str) -> Optional[RouteConfig]:
    """Get route configuration for a fal.ai endpoint ID."""
    # Exact match
    if endpoint_id in ROUTE_MAP:
        return ROUTE_MAP[endpoint_id]

    # Wildcard matching for patterns like "fal-ai/kling-video/*"
    for pattern, config in ROUTE_MAP.items():
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            if endpoint_id.startswith(prefix):
                return config

    return None


def list_available_endpoints() -> list:
    """Return list of available endpoint IDs."""
    return list(ROUTE_MAP.keys())
