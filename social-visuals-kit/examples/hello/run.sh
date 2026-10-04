#!/usr/bin/env bash
# Offline end-to-end test: synthetic footage -> card -> reel (4:5 and article-wide) -> checks. No API spend.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p out
ffmpeg -y -loglevel error -f lavfi -i testsrc2=size=1280x720:rate=30:duration=8 -pix_fmt yuv420p out/footage.mp4
./run.sh tools/card.py compare --size portrait --out out/hello_compare.png \
  --set title="Before and *after*" --set left_label="Before" --set left="Long posts\nNo hook" --set right_label="After" --set right="One idea\nHook first"
./run.sh tools/reel.py examples/hello/reel.json
./run.sh tools/reel.py examples/hello/reel.json --canvas wide --out out/hello_wide.mp4
./run.sh tools/qa.py check out/hello.mp4 feed_portrait
./run.sh tools/qa.py sheet out/hello.mp4 out/hello_sheet.png --every 1
echo; echo "Open out/hello_sheet.png, out/hello_compare.png and out/hello_poster.png and look at them."
