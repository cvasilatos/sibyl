# Sibyl

LLM-powered research paper review system that runs open-source models locally (Ollama, vLLM, or an OpenAI-compatible server).

## Layout

- `backend/`: Python package `sibyl` (FastAPI). Self-contained: own `pyproject.toml`, `uv.lock`, `ruff.toml`, `.pre-commit-config.yaml`, `Dockerfile`.
  - `main.py`: the FastAPI app and `run_server()` (the `sibyl` command). Routers are mounted under `/api` and `/ws`.
  - `routers/web_*.py`: HTTP and WebSocket endpoints. `web/model/`: their pydantic request and response models.
  - `inference/`: pluggable engines (`base.py`, `ollama_engine.py`, `vllm_engine.py`, `openai_engine.py`), picked with `SIBYL_ENGINE`.
  - `reviewer.py`, `comparison.py`, `pdf_parser.py`, `figures.py`, `conferences.py`, `hardware.py`: review pipeline, PDF and figure handling, conference forms, GPU info.
  - `storage/`: review persistence. `services/`: model catalog.
  - `resources/`: review prompt and conference templates (`conferences/*.json`, one per venue).
  - `config.py`: settings from `SIBYL_*` env vars or `backend/.env`; document new ones in `backend/.env.example`.
- `backend/tests/`: pytest. `fake_vllm.py` stands in for a vLLM server.
- `web/`: Next.js app (App Router) in `src/app/`, components in `src/components/` (shadcn primitives in `ui/`), API calls in `src/lib/api.ts`, Vitest tests in `src/__tests__/`.
- `docker-compose.yml` (Ollama, one container per GPU) and `docker-compose.vllm.yml` (vLLM). `scripts/run-macos.sh` runs everything natively on Apple Silicon.
- `docs/`: design notes and decisions. `tmp/`: scratch, ignored by git.

## Commands

- Backend (in `backend/`): `uv sync --all-groups` (pytest lives in the `test` group); run with `uv run sibyl`. Add dependencies with `uv add <pkg>`, never `pip install`.
- Before finishing a backend change: `uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run pytest`.
- Web (in `web/`): `npm install`; run with `npm run dev` (expects the backend on :8000).
- Before finishing a web change: `npm run check && npm test && npm run build`.
- CI: `.github/workflows/backend-ci.yml` and `frontend-ci.yml`.
- Git hooks (pre-commit, config in `backend/`) run ruff, uv lock, ty and pytest. If a hook fails, fix the cause and commit again; never bypass with `--no-verify` unless the user asks.

## Conventions

- Keep routers thin; put logic in the pipeline modules or `services/`.
- A new conference form is a JSON file in `resources/conferences/`; no code change needed.
- Put scratch files in `tmp/` or the session scratchpad, never next to source.
