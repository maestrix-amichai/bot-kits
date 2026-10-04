#!/usr/bin/env python3
"""Generate the example's inputs locally (no API): a still, a tone and its transcript JSON."""
import json
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "tools"))
import mv  # noqa: E402

A = mv.WORK / "hello"
A.mkdir(parents=True, exist_ok=True)

# a gradient "hero" still
W, H = 1920, 1080
img = Image.new("RGB", (W, H))
px = img.load()
for y in range(H):
    for x in range(0, W, 1):
        px[x, y] = (int(40 + 60 * x / W), int(30 + 90 * y / H), int(120 + 100 * (1 - x / W)))
d = ImageDraw.Draw(img)
d.ellipse([W // 2 - 260, H // 2 - 260, W // 2 + 260, H // 2 + 260], outline=(255, 255, 255), width=8)
img.save(A / "hero.png")

# a 6 s two-tone "call" so the waveform scene has something to draw
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=3",
                "-f", "lavfi", "-i", "sine=frequency=330:duration=3", "-filter_complex",
                "[0:a]tremolo=f=4:d=0.8[a];[1:a]tremolo=f=6:d=0.9[b];[a][b]concat=n=2:v=0:a=1,volume=5,alimiter=limit=0.9", "-ar", "24000", "-ac", "1",
                str(A / "call.wav")], check=True)
(A / "call.json").write_text(json.dumps([
    {"start": 0.3, "end": 2.6, "speaker": "A", "text": "Good morning, how can I help?"},
    {"start": 3.2, "end": 5.6, "speaker": "B", "text": "I would like to book a room."},
]))
print("assets ->", A)
