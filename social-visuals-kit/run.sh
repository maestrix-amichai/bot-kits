#!/usr/bin/env bash
# Run any kit tool with the venv active and (optionally) secrets injected.
#   ./run.sh tools/reel.py spec.json
# Secrets: set SECRETS_CMD to your secrets runner, e.g.  SECRETS_CMD="doppler run --"  (or "op run --").
# Optional: PW_MODULE / CHROME_BIN point at an existing Playwright install; BRAND points at a brand.json.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[ -d .venv ] && source .venv/bin/activate
export NODE_PATH="$PWD/node_modules${NODE_PATH:+:$NODE_PATH}"
case "$1" in *.py) RUN=(python3 "$@");; *.js) RUN=(node "$@");; *) RUN=("$@");; esac
if [ -n "${SECRETS_CMD:-}" ]; then exec $SECRETS_CMD "${RUN[@]}"; else exec "${RUN[@]}"; fi
