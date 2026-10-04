#!/usr/bin/env python3
"""Phrase-level transcription with timestamps, written as JSON.

  ./run.sh tools/gemini_transcribe.py work/vo1.wav [work/vo1.json]

Output: [{"start": 0.0, "end": 2.4, "speaker": "A", "text": "..."}]. Feed the JSON to a scene as
"caps_from" in scenes.json so captions follow the audio. For video files, extract audio first:
  ffmpeg -y -i clip.mp4 -vn -ac 1 -ar 16000 clip.wav
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("out", nargs="?")
    a = ap.parse_args()
    try:
        phrases = mv.transcribe(a.audio)
    except RuntimeError as e:
        raise SystemExit(f"transcription failed: {e}")
    text = json.dumps(phrases, indent=1, ensure_ascii=False)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(text)


if __name__ == "__main__":
    main()
