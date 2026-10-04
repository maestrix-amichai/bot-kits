#!/usr/bin/env python3
"""Shared helpers for the video pipeline kit. Standard library + Pillow only.

Everything is relative to the kit folder, so the kit can live anywhere:
  work/  intermediate files and generated assets (persistent; never /tmp)
  out/   finished films, storyboards, review frames
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

KIT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ.get("KIT_WORK", KIT / "work"))
OUT = pathlib.Path(os.environ.get("KIT_OUT", KIT / "out"))
API = "https://generativelanguage.googleapis.com/v1beta"

# Default models. Override with env vars (see .env.example) when Google renames or retires one.
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
TTS_MODEL = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
TEXT_MODEL = os.environ.get("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
VEO_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-fast-generate-preview")


# ── environment / keys ─────────────────────────────────────────────────────────
def load_dotenv() -> None:
    """Fill os.environ from KIT/.env for names not already set (Doppler and the shell win)."""
    f = KIT / ".env"
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def gemini_key() -> str:
    load_dotenv()
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit(
            "No GEMINI_API_KEY in the environment.\n"
            "  Run through the wrapper so Doppler injects it:  ./run.sh tools/<script>.py ...\n"
            "  (one-time: `doppler setup` in this folder, see docs/DOPPLER.md), or put the key in .env"
        )
    return key


def ensure_dirs() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)


# ── Gemini REST (no SDK: one less dependency, same calls the SDK makes) ────────
def _request(url: str, body: dict | None, key: str, timeout: int, method: str | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method or ("POST" if body is not None else "GET"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def api(path: str, body: dict | None = None, timeout: int = 180, retries: int = 3) -> dict:
    """POST (or GET when body is None) to the Gemini API. Retries 429/5xx with backoff."""
    key = gemini_key()
    url = path if path.startswith("http") else f"{API}/{path}"
    last = ""
    for attempt in range(retries):
        try:
            return _request(url, body, key, timeout)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}"
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
                continue
            break
        except (urllib.error.URLError, TimeoutError) as e:
            last = f"network: {e}"
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
                continue
            break
    raise RuntimeError(last)


def generate(model: str, parts: list, config: dict | None = None, timeout: int = 180) -> dict:
    body = {"contents": [{"parts": parts}]}
    if config:
        body["generationConfig"] = config
    return api(f"models/{model}:generateContent", body, timeout=timeout)


def b64_file(path: str | pathlib.Path) -> str:
    return base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def mime_for(path: str | pathlib.Path) -> str:
    try:  # sniff images by content: an API reply can be JPEG bytes in a file the caller named .png
        head = pathlib.Path(path).read_bytes()[:12]
        if head.startswith(b"\x89PNG"):
            return "image/png"
        if head.startswith(b"\xff\xd8"):
            return "image/jpeg"
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return "image/webp"
    except OSError:
        pass
    ext = pathlib.Path(path).suffix.lower()
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
            ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".mp4": "video/mp4"}.get(ext, "application/octet-stream")


def first_json(text: str):
    """Parse the first JSON value in a model reply that may be wrapped in ``` fences or prose."""
    text = text.strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        if opener in text and closer in text:
            i, j = text.index(opener), text.rindex(closer)
            try:
                return json.loads(text[i:j + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(text)


def reply_text(resp: dict) -> str:
    parts = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


# ── audio helpers ──────────────────────────────────────────────────────────────
def write_wav(path: str | pathlib.Path, pcm: bytes, rate: int = 24000) -> float:
    hdr = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16, 1, 1,
                      rate, rate * 2, 2, 16, b"data", len(pcm))
    pathlib.Path(path).write_bytes(hdr + pcm)
    return len(pcm) / rate / 2


def transcribe(wav: str | pathlib.Path) -> list[dict]:
    """Phrase-level transcription with timestamps: [{start,end,speaker,text}]."""
    prompt = ("Transcribe this audio verbatim. Return ONLY a JSON array of phrases: "
              '[{"start": seconds, "end": seconds, "speaker": "A|B", "text": "..."}], one entry per '
              "spoken phrase (split at pauses), timestamps in seconds with one decimal. Write non-speech "
              "events as text in square brackets, for example [phone rings].")
    r = generate(TEXT_MODEL, [{"inlineData": {"mimeType": mime_for(wav), "data": b64_file(wav)}}, {"text": prompt}],
                 {"responseMimeType": "application/json"}, timeout=240)
    data = first_json(reply_text(r))
    return data if isinstance(data, list) else data.get("phrases", [])


def norm_words(t: str) -> list[str]:
    """Lower-case word list for word-for-word transcript comparison."""
    t = t.lower().replace("\u2019", "'").replace("\u20ac", " euros ").replace("%", " percent ")
    return re.sub(r"[^a-z0-9\u00e0-\u00ff' ]+", " ", t).split()


def spoken(line: str) -> str:
    """Text to hand a video model to say aloud: dashes become commas (a dash gets voiced as a stray word)."""
    return line.replace(" \u2014 ", ", ").replace("\u2014", ",").replace(" - ", ", ").replace("\u2013", ",")


# ── ffmpeg ─────────────────────────────────────────────────────────────────────
def run(label: str, cmd: list[str], quiet: bool = False) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode:
        raise SystemExit(f"{label} failed:\n{r.stderr[-2000:]}")
    if not quiet:
        print("built", label)


def probe_duration(path: str | pathlib.Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def has_audio(path: str | pathlib.Path) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return "audio" in r.stdout


def need_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg not found. Run: bash bootstrap.sh")


# ── fonts and caption pills (Pillow; ffmpeg drawtext is not used anywhere) ─────
def _font_candidates() -> list[str]:
    env = os.environ.get("KIT_FONT")
    found = [env] if env else []
    found += [str(p) for p in sorted((KIT / "assets" / "fonts").glob("*.ttf"))]
    found += [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    return found


def load_font(size: int, weight: int = 800):
    from PIL import ImageFont
    for path in _font_candidates():
        if not path or not os.path.exists(path):
            continue
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            continue
        try:  # variable fonts (Inter): pick the heavy weight
            axes = font.get_variation_axes()
            vals = []
            for ax in axes:
                name = ax.get("name", b"")
                name = name.decode() if isinstance(name, bytes) else str(name)
                vals.append(max(ax["minimum"], min(ax["maximum"], weight)) if "eight" in name else ax["default"])
            font.set_variation_by_axes(vals)
        except Exception:
            pass
        return font
    return ImageFont.load_default(size)


def hex_rgba(value, default=(255, 255, 255, 255)):
    """'#rrggbb' or '#rrggbbaa' (or an [r,g,b,(a)] list) to an RGBA tuple."""
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        v = list(value) + [255] * (4 - len(value))
        return tuple(int(x) for x in v[:4])
    s = str(value).lstrip("#")
    if len(s) == 6:
        s += "ff"
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4, 6))


def hex_rgb_str(value, default="0d0d10") -> str:
    """ffmpeg colour string 0xRRGGBB."""
    r, g, b, _ = hex_rgba(value, hex_rgba("#" + default))
    return f"0x{r:02x}{g:02x}{b:02x}"


def pill(text: str, out: str | pathlib.Path, width: int, size: int = 52, fg=(255, 255, 255, 255),
         bg=(13, 13, 16, 220), pad_x: int = 48, pad_y: int = 26, plain: bool = False) -> int:
    """Render one caption to a transparent PNG `width` wide. Returns its height.
    plain=True draws bare text (no pill), used for titles on cards."""
    from PIL import Image, ImageDraw
    f = load_font(size)
    bb = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if plain:
        img = Image.new("RGBA", (width, th + 60), (0, 0, 0, 0))
        ImageDraw.Draw(img).text(((width - tw) // 2 - bb[0], 30 - bb[1]), text, font=f, fill=fg)
    else:
        bw, bh = tw + pad_x * 2, th + pad_y * 2
        img = Image.new("RGBA", (width, bh + 24), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x0 = (width - bw) // 2
        d.rounded_rectangle([x0, 12, x0 + bw, 12 + bh], radius=bh // 2, fill=bg)
        d.text(((width - tw) // 2 - bb[0], 12 + pad_y - bb[1]), text, font=f, fill=fg)
    img.save(out)
    return img.height
