#!/usr/bin/env bash
# Live check of the Gemini tools (costs a few cents): one image, one voice line, its transcript,
# composed into a 7 second film with the voiceover and captions that follow it.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
mkdir -p work/live
./run.sh tools/gemini_image.py "A bright minimal flat illustration of a film clapperboard on a soft blue background, no text" work/live/hero.png
./run.sh tools/gemini_tts.py "Welcome to the kit. This is a short voiceover test." work/live/vo.wav Kore "Say warmly and unhurried:"
./run.sh tools/gemini_transcribe.py work/live/vo.wav work/live/vo.json >/dev/null
./run.sh tools/compose.py examples/live/scenes.json --review
echo; echo "Open out/live.mp4"
