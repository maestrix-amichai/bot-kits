#!/usr/bin/env bash
# One-shot setup for the video pipeline kit. Safe to re-run. Installs whatever is missing:
#   ffmpeg, python3 (+venv, Pillow), node (+Playwright and its Chromium), Doppler CLI, a caption font.
# macOS (Homebrew) and Debian/Ubuntu (apt). Windows: use WSL2 with Ubuntu.
#   bash bootstrap.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m!! %s\033[0m\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
PYTHON="${PYTHON:-python3}"
OS="$(uname -s)"

say "System tools (ffmpeg, python3, node, doppler)"
if [ "$OS" = "Darwin" ]; then
  if ! have brew; then
    say "Installing Homebrew (it asks for your Mac password once)"
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
  fi
  have ffmpeg  || brew install ffmpeg
  have "$PYTHON" || brew install python
  have node    || brew install node
  have doppler || brew install dopplerhq/cli/doppler
elif [ "$OS" = "Linux" ] && have apt-get; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO apt-get update -y
  have ffmpeg    || $SUDO apt-get install -y ffmpeg
  have "$PYTHON" || $SUDO apt-get install -y python3
  $SUDO apt-get install -y python3-venv python3-pip curl gnupg ca-certificates
  have node      || { curl -fsSL https://deb.nodesource.com/setup_22.x | $SUDO -E bash - && $SUDO apt-get install -y nodejs; }
  have doppler   || { curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | $SUDO sh; }
else
  echo "Unsupported OS ($OS). On Windows use WSL2 (Ubuntu) and run this there." >&2; exit 1
fi

"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "Python 3.9+ is required (found: $("$PYTHON" --version 2>&1))" >&2; exit 1; }
node -e 'process.exit(+process.versions.node.split(".")[0] >= 18 ? 0 : 1)' || { echo "Node 18+ is required (found: $(node --version))" >&2; exit 1; }

say "Python environment (.venv, Pillow)"
[ -d .venv ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

say "Playwright and its Chromium browser"
npm install --no-audit --no-fund --loglevel=error
if [ "$OS" = "Linux" ]; then npx --yes playwright install --with-deps chromium; else npx --yes playwright install chromium; fi

say "Caption font"
if ! ls assets/fonts/*.ttf >/dev/null 2>&1; then
  mkdir -p assets/fonts
  curl -fsSL -o "assets/fonts/Inter[opsz,wght].ttf" "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf" \
    && curl -fsSL -o assets/fonts/OFL.txt "https://github.com/google/fonts/raw/main/ofl/inter/OFL.txt" \
    || warn "font download failed: captions will use a system font"
else
  echo "font present"
fi

mkdir -p work out
chmod +x run.sh bootstrap.sh tools/*.py tools/*.js examples/hello/*.sh 2>/dev/null || true

say "Checking the setup"
.venv/bin/python tools/doctor.py --offline || true

cat <<'MSG'

Next, give the kit its Gemini key (one time, see docs/DOPPLER.md):
  doppler login
  doppler setup            # pick the project and config that holds GEMINI_API_KEY
Then verify, including a live key check:
  ./run.sh tools/doctor.py
And try the offline example (no API key needed):
  bash examples/hello/run.sh
MSG
