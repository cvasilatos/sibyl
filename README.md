# Sibyl 🔮

An LLM-powered research paper review system that leverages local open-source AI models to provide comprehensive, comparative reviews of academic papers.

## Repository Structure

This repository is organized into two self-contained sub-projects:

| Directory | Description |
|-----------|-------------|
| [`backend/`](./backend/) | Python / FastAPI API server |
| [`web/`](./web/) | Next.js frontend |

Each sub-directory contains its own `README.md`, `Dockerfile`, and all files needed to develop, test, and deploy that component independently.

## Inference Engines

Sibyl runs open-source models through a pluggable engine, chosen with `SIBYL_ENGINE` in `backend/.env`.
Downloading and removing models from the **Models** tab works the same way with every engine that supports it.

| Engine | Best for | Models from | Platforms |
|--------|----------|-------------|-----------|
| `ollama` (default) | Simplest setup, Macs, quick experiments | Ollama library | Linux (NVIDIA), macOS (Metal) |
| `vllm` | Throughput on NVIDIA GPU servers: continuous batching, PagedAttention, fast long-context prefill | Hugging Face Hub | Linux + NVIDIA |
| `openai` | A server you already run (LM Studio, llama.cpp server, SGLang) | Managed by that server | Any |

With `vllm`, Sibyl downloads Hugging Face models into the HF cache and starts `vllm serve` on the GPU picked in the
UI when a review needs it. Reviews of the same model on the same GPU share one server, so vLLM batches them.
Asking for a different model on that GPU swaps the server once running reviews finish. Server logs go to `backend/logs/vllm-gpu<N>.log`.

Every engine sizes the context window to the paper (up to `SIBYL_MAX_CONTEXT`, default 32k tokens). If a paper
does not fit, its end (references/appendix) is trimmed and the UI says so, instead of the model silently seeing only the first few pages.

## Conference Review Templates

The **Conference Review Template** selector on the Review tab makes the model fill in the official reviewer form of a
top venue. Templates live in [`backend/src/sibyl/resources/conferences/`](backend/src/sibyl/resources/conferences/),
one JSON file per conference. Each question becomes a required field of the JSON schema the model is constrained
to, and each rating uses the conference's own scale. Even a small model therefore answers every question with a valid score.
The completed form is shown in the results and stored in the library next to Sibyl's normalized review.

To add or update a conference, copy an existing JSON file and edit `questions`. Each question is either
`{"type": "text"}` or `{"type": "choice", "options": [{"value": 4, "label": "excellent"}, ...]}`.
The template is picked up on the next backend start. You can still upload any free-form `.txt`/`.md` form instead.

## Quick Start: macOS (Apple Silicon)

Docker on macOS cannot use the Apple GPU, so Sibyl runs natively:

```bash
brew install ollama uv node     # once
./scripts/run-macos.sh          # starts Ollama (Metal), the backend and the web app
# open http://localhost:3000
```

The script pulls `qwen3:8b` on first run (choose another with `SIBYL_DEFAULT_MODEL=...`). PDF parsing runs on the
Apple GPU (MPS), and the GPU tab shows Apple GPU load and unified memory. On 16 GB Macs, set `SIBYL_MAX_CONTEXT=16384`.

## Quick Start: Linux GPU server (Docker Compose)

```bash
cp backend/.env.example backend/.env

# Option A: Ollama, one container per GPU
docker compose up -d
docker compose exec ollama-0 ollama pull qwen3:8b

# Option B: vLLM, faster on NVIDIA. Download models from the Models tab.
mkdir -p /data/cv43/sibyl/hf_cache
docker compose -f docker-compose.vllm.yml up -d --build

# open http://localhost:4000
```

Gated Hugging Face models (Llama, Gemma) need `HF_TOKEN` in `backend/.env`. Reviews are stored per embedding backend,
so reviews made with the Ollama setup do not show up in the vLLM setup's library, and the reverse.

## Development

### Backend (Python / FastAPI)

```bash
cd backend

# Install dependencies (requires uv)
uv sync --extra web --extra dev

# Start the API server
sibyl --host 0.0.0.0 --port 8000 --log-level INFO

# Run tests
pytest
```

See [`backend/README.md`](./backend/README.md) for full documentation.

### Frontend (Next.js)

```bash
cd web

# Install dependencies
npm install

# Start the development server
npm run dev

# Open http://localhost:3000
```

See [`web/README.md`](./web/README.md) for full documentation.
