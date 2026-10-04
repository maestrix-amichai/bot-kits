#!/usr/bin/env bash
# One-shot setup. Safe to re-run. macOS (Homebrew) or Debian/Ubuntu (apt). Windows: use WSL2.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
say(){ printf '\n==> %s\n' "$*"; }
have(){ command -v "$1" >/dev/null 2>&1; }
OS="$(uname -s)"
say "System tools: ffmpeg, python3, node, git"
if [ "$OS" = "Darwin" ]; then
  have brew || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
  have ffmpeg  || brew install ffmpeg
  have python3 || brew install python
  have node    || brew install node
  have git     || brew install git
elif [ "$OS" = "Linux" ] && have apt-get; then
  S=""; [ "$(id -u)" -ne 0 ] && S="sudo"
  $S apt-get update -y
  have ffmpeg  || $S apt-get install -y ffmpeg
  have python3 || $S apt-get install -y python3 python3-venv python3-pip
  have node    || $S apt-get install -y nodejs npm
  have git     || $S apt-get install -y git
else
  echo "Unsupported OS: install ffmpeg, python3, node, git by hand"; exit 1
fi
say "Python environment (.venv)"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
say "Playwright and its browser"
npm install --silent
npx playwright install chromium
[ -f brand/brand.json ] || cp brand/brand.example.json brand/brand.json
say "Done. Next: ./run.sh tools/doctor.py   then   bash examples/hello/run.sh"
