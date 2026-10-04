#!/usr/bin/env bash
# Offline end-to-end check: generate assets -> record a page -> compose a film. No API key needed.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
./run.sh examples/hello/make_assets.py
./run.sh tools/record.js examples/hello/recipe.json
./run.sh tools/compose.py examples/hello/scenes.json --review
echo; echo "Open out/hello.mp4 and out/hello_review/contact.png"
