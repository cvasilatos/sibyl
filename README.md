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

Every engine gives the review the full context window (`SIBYL_MAX_CONTEXT`, default 32k tokens, capped by the
model's own limit with Ollama and vLLM; `SIBYL_MAX_CONTEXT=model` uses each model's full limit, which needs plenty of
VRAM because the engine reserves memory for the whole window), and the model may write until it is full: there is no output-token limit. If a paper
does not leave room for the review, its end (references/appendix) is trimmed and the UI says so, instead of the model
silently seeing only the first few pages.

## Review Length and Mode

The Review tab sets how long the review should be (default `SIBYL_REVIEW_DETAIL`). **Model decides** (the default)
gives no length guidance. **Concise**, **standard** and **detailed** tell the model how many paragraphs to write per
section and how many suggestions to give, for models whose reviews come out too short; this is guidance in the prompt,
not a token limit. **Section by section** mode (default `SIBYL_REVIEW_MODE`) writes
each section, or each open question of a conference form, in its own call, showing the model what it already wrote,
then asks for the ratings, score and recommendation. Small models write much longer reviews this way, at the cost of
one call per section. Custom forms have no fixed sections and are always reviewed in one call.

Every review stores the settings that produced it (engine, model, length, mode, temperature, context, form, vision
model, related work, GPU, time taken). They are shown under the review on the Review tab and in the Library.

## Related Work Search

Before reviewing, the review model writes a few keyword searches from the paper's title, abstract and introduction.
Sibyl runs them on arXiv, and the model picks the most relevant results and notes how each relates to the paper.
The reviewer sees these abstracts and cites them as [R1], [R2], ... when judging novelty. The papers are listed
under the review and in the `.txt` export.
Only the search keywords leave the machine, never the paper. Turn the search off per review on the Review tab,
or by default with `SIBYL_RELATED_WORK=false`. If arXiv is unreachable, the review goes ahead without related work.

## Conference Review Templates

The **Conference Review Template** selector on the Review tab makes the model fill in the official reviewer form of a
top venue. Templates live in [`backend/src/sibyl/resources/conferences/`](backend/src/sibyl/resources/conferences/),
one JSON file per conference. Each question becomes a required field of the JSON schema the model is constrained
to, and each rating uses the conference's own scale. Even a small model therefore answers every question with a valid score.
The completed form is shown in the results and stored in the library next to Sibyl's normalized review.

The selector also shows each venue's submission page limit (`page_limit` in the JSON), taken from the newest
official call for papers and linked to it.

To add or update a conference, copy an existing JSON file and edit `questions`. Each question is either
`{"type": "text"}` or `{"type": "choice", "options": [{"value": 4, "label": "excellent"}, ...]}`.
The template is picked up on the next backend start. You can still upload any free-form `.txt`/`.md` form instead.

## Quick Start: any platform (`sibyl run`)

With [uv](https://docs.astral.sh/uv/), Node.js 20+ and a model server already running (Ollama by default, or set
`SIBYL_ENGINE` in `backend/.env`), one command starts the backend and the web app on Linux, macOS or Windows:

```bash
cd backend
uv run sibyl run                 # backend on :8000, web app on http://localhost:3000; Ctrl+C stops both
uv run sibyl run --help          # ports, host, HTTPS, log level
```

It installs the web dependencies on first run. `uv run sibyl serve` starts only the backend.

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
uv run sibyl serve --host 0.0.0.0 --port 8000 --log-level INFO

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
