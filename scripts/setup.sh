#!/usr/bin/env bash
# Memory Séance Lite setup for macOS and Linux.
#   ./scripts/setup.sh          default model (gemma3:1b)
#   ./scripts/setup.sh --low    very low-resource model (qwen3:0.6b)
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL="gemma3:1b"
[ "${1:-}" = "--low" ] && MODEL="qwen3:0.6b"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "Python 3.10 or newer is required. Install it from https://www.python.org/downloads/" >&2
  exit 1
fi

[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install --quiet -r requirements.txt
[ -f .env ] || cp .env.example .env
sed -i.bak "s/^MSL_MODEL=.*/MSL_MODEL=$MODEL/" .env && rm -f .env.bak

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama is not installed. Get it from https://ollama.com/download, then run:  ollama pull $MODEL"
elif ! ollama list >/dev/null 2>&1; then
  echo "Ollama is installed but not running. Start it (open the app or run 'ollama serve'), then run:  ollama pull $MODEL"
else
  ollama pull "$MODEL"
fi

echo
echo "Setup done. Start the app with:"
echo "  .venv/bin/python -m app.main"
echo "Then open http://127.0.0.1:8000"
