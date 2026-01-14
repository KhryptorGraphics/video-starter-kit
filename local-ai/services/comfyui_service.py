#!/usr/bin/env python3
"""
ComfyUI Service Wrapper

This script starts ComfyUI on port 10001 (internal 8188).
ComfyUI has its own API, so this is just a launcher.

Port: 10001
Conda env: comfyui
"""

import os
import sys
import subprocess
import signal

# ComfyUI installation path
COMFYUI_PATH = os.getenv("COMFYUI_PATH", "/home/kp/ComfyUI")
COMFYUI_PORT = int(os.getenv("COMFYUI_PORT", "8188"))  # Internal port

def main():
    """Start ComfyUI server."""
    print(f"Starting ComfyUI from {COMFYUI_PATH} on port {COMFYUI_PORT}...")

    # Change to ComfyUI directory
    os.chdir(COMFYUI_PATH)

    # Start ComfyUI
    cmd = [
        sys.executable,
        "main.py",
        "--listen", "0.0.0.0",
        "--port", str(COMFYUI_PORT),
        "--preview-method", "auto",
    ]

    print(f"Running: {' '.join(cmd)}")

    # Run ComfyUI
    process = subprocess.Popen(cmd)

    def signal_handler(sig, frame):
        print("Shutting down ComfyUI...")
        process.terminate()
        process.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Wait for process
    process.wait()


if __name__ == "__main__":
    main()
