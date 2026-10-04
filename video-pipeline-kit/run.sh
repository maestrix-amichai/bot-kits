#!/usr/bin/env bash
# Run any kit script with the venv active and GEMINI_API_KEY injected.
#   ./run.sh tools/compose.py examples/hello/scenes.json
#   ./run.sh tools/gemini_image.py "a sunny hotel lobby" work/lobby.png
# Key order: already in the environment > .env file > Doppler (the folder's `doppler setup`).
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1
export PATH="$PWD/.venv/bin:$PATH"
if [ -z "${GEMINI_API_KEY:-}" ] && [ -z "${GOOGLE_API_KEY:-}" ]; then
  if [ -f .env ]; then
    set -a; . ./.env; set +a
  elif command -v doppler >/dev/null 2>&1 && doppler secrets get GEMINI_API_KEY --plain >/dev/null 2>&1; then
    exec doppler run -- "$0" "$@"
  fi
fi
[ $# -gt 0 ] || { echo "usage: ./run.sh <script.py|script.js|command> [args...]" >&2; exit 2; }
case "$1" in
  *.py) exec python "$@" ;;
  *.js|*.mjs) exec node "$@" ;;
  *) exec "$@" ;;
esac
