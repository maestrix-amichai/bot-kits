#!/usr/bin/env python3
"""Text to speech with Gemini, written as a 24 kHz mono WAV.

  ./run.sh tools/gemini_tts.py "Hello there." work/vo1.wav [voice] [style prefix]

Voices: Kore (f, firm)  Aoede (f, breezy)  Leda (f, youthful)  Zephyr (f, bright)
        Puck (m, upbeat)  Charon (m, informative)  Orus (m, firm)  Fenrir (m, excitable)
The optional style prefix steers delivery, e.g. "Say warmly, unhurried:".
Model: GEMINI_TTS_MODEL (default gemini-2.5-flash-preview-tts).
"""
import argparse
import base64
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text")
    ap.add_argument("out")
    ap.add_argument("voice", nargs="?", default="Kore")
    ap.add_argument("style", nargs="?", default="")
    a = ap.parse_args()

    text = (a.style + "\n" if a.style else "") + a.text
    cfg = {"responseModalities": ["AUDIO"],
           "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": a.voice}}}}
    try:
        r = mv.generate(mv.TTS_MODEL, [{"text": text}], cfg, timeout=180)
    except RuntimeError as e:
        raise SystemExit(f"tts failed: {e}")
    part = r["candidates"][0]["content"]["parts"][0]["inlineData"]
    rate = int(re.search(r"rate=(\d+)", part.get("mimeType", "rate=24000")).group(1))
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    secs = mv.write_wav(out, base64.b64decode(part["data"]), rate)
    print(f"saved {out} ({secs:.2f}s, {a.voice})")


if __name__ == "__main__":
    main()
