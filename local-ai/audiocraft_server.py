#!/usr/bin/env python3
"""
Audiocraft Gradio Server for music generation.
Exposes MusicGen via a Gradio API on port 8000.
"""

import gradio as gr
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write
import torch
import tempfile
import os

print("Loading MusicGen model...")
model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(duration=30)
print("Model loaded successfully!")


def generate_music(prompt: str, duration: int = 30) -> str:
    """Generate music from a text prompt."""
    print(f"Generating music: '{prompt}' for {duration}s")
    model.set_generation_params(duration=int(duration))
    wav = model.generate([prompt])

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        output_path = f.name[:-4]  # Remove .wav extension for audio_write
        audio_write(output_path, wav[0].cpu(), model.sample_rate, strategy='loudness')
        result_path = output_path + '.wav'
        print(f"Generated: {result_path}")
        return result_path


# Create Gradio interface
demo = gr.Interface(
    fn=generate_music,
    inputs=[
        gr.Textbox(label="Prompt", placeholder="A jazzy piano melody with drums"),
        gr.Slider(minimum=5, maximum=60, value=30, step=1, label="Duration (seconds)")
    ],
    outputs=gr.Audio(label="Generated Music"),
    title="MusicGen - Audio Generation",
    description="Generate music from text prompts using Meta's MusicGen model."
)

if __name__ == "__main__":
    print("Starting Gradio server on port 8000...")
    demo.launch(server_name='0.0.0.0', server_port=8000)
