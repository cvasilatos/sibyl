#!/usr/bin/env bash
# Run Sibyl natively on macOS (Apple Silicon). Docker on macOS cannot use the Apple GPU (Metal),
# so Ollama, the backend and the web app run directly on the host instead.
#
#   ./scripts/run-macos.sh                 # start everything
#   SIBYL_DEFAULT_MODEL=gemma3:12b ./scripts/run-macos.sh
#
# Environment:
#   SIBYL_DEFAULT_MODEL  model pulled on first run if no model is installed (default: qwen3:8b)
#   SIBYL_ENGINE         ollama (default) or openai (e.g. LM Studio at SIBYL_OPENAI_BASE_URL)
#   BACKEND_PORT / WEB_PORT  (default: 8000 / 3000)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
DEFAULT_MODEL="${SIBYL_DEFAULT_MODEL:-qwen3:8b}"
export SIBYL_ENGINE="${SIBYL_ENGINE:-ollama}"

say() { printf '\033[1;35m[sibyl]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[sibyl]\033[0m %s\n' "$*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "This script is for macOS. On Linux with NVIDIA GPUs use docker compose (see README)."
[[ "$(uname -m)" == "arm64" ]] || say "Intel Mac detected: models will run on the CPU and be slow."

command -v uv >/dev/null || die "uv is required: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v npm >/dev/null || die "Node.js 20+ is required: brew install node"

PIDS=()
cleanup() {
  say "Stopping..."
  for pid in "${PIDS[@]:-}"; do [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

if [[ "$SIBYL_ENGINE" == "ollama" ]]; then
  command -v ollama >/dev/null || die "Ollama is required: brew install ollama (or download it from https://ollama.com/download)"
  export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
  if ! curl -sf "$OLLAMA_BASE_URL/api/version" >/dev/null; then
    mkdir -p "$ROOT/backend/logs"
    say "Starting Ollama (Metal) with flash attention and an 8-bit KV cache for long papers..."
    OLLAMA_FLASH_ATTENTION="${OLLAMA_FLASH_ATTENTION:-1}" OLLAMA_KV_CACHE_TYPE="${OLLAMA_KV_CACHE_TYPE:-q8_0}" \
      ollama serve >"$ROOT/backend/logs/ollama.log" 2>&1 &
    PIDS+=($!)
    for _ in $(seq 1 30); do curl -sf "$OLLAMA_BASE_URL/api/version" >/dev/null && break; sleep 1; done
    curl -sf "$OLLAMA_BASE_URL/api/version" >/dev/null || die "Ollama did not start; see backend/logs/ollama.log"
  fi
  if [[ "$(ollama list | tail -n +2 | grep -vc nomic-embed-text || true)" == "0" ]]; then
    say "No models installed yet; pulling $DEFAULT_MODEL (change with SIBYL_DEFAULT_MODEL)..."
    ollama pull "$DEFAULT_MODEL"
  fi
fi

say "Installing backend dependencies..."
(cd "$ROOT/backend" && env -u VIRTUAL_ENV uv sync --quiet)
[[ -f "$ROOT/backend/.env" ]] || cp "$ROOT/backend/.env.example" "$ROOT/backend/.env"

say "Starting backend on http://localhost:$BACKEND_PORT ..."
(cd "$ROOT/backend" && env -u VIRTUAL_ENV uv run sibyl --host 127.0.0.1 --port "$BACKEND_PORT" --log-level INFO) &
PIDS+=($!)

say "Starting web app on http://localhost:$WEB_PORT ..."
(cd "$ROOT/web" && { [[ -d node_modules/next ]] || npm ci --no-audit --no-fund; } && NEXT_PUBLIC_API_URL="http://localhost:$BACKEND_PORT" npm run dev -- -p "$WEB_PORT") &
PIDS+=($!)

say "Sibyl is starting. Open http://localhost:$WEB_PORT (Ctrl+C to stop)."
wait
