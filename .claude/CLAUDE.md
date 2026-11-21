# Sibyl

LLM-powered research paper review system that runs open-source models locally (Ollama, vLLM, or an OpenAI-compatible server).

## Layout

- `backend/`: Python package `sibyl` (FastAPI). Self-contained: own `pyproject.toml`, `uv.lock`, `ruff.toml`, `.pre-commit-config.yaml`, `Dockerfile`.
  - `main.py`: the FastAPI app and `run_server()` (the `sibyl` command). Routers are mounted under `/api` and `/ws`. `openapi.py` exports the API schema without starting a server.
  - `routers/`: HTTP and WebSocket endpoints (`reviews`, `upload`, `ws`, `gpu`, `conferences`). `schemas/`: their pydantic request and response models; `tests/schemas/test_responses.py` checks no model drops a field its producer returns. `state.py`: shared app state.
  - `services/`: the review pipeline and helpers (`reviewer`, `comparison`, `pdf_parser`, `figures`, `conferences`, `hardware`, `model_catalog`).
  - `inference/`: pluggable engines (`base.py`, `ollama_engine.py`, `vllm_engine.py`, `openai_engine.py`), picked with `SIBYL_ENGINE`.
  - `storage/`: review persistence.
  - `resources/`: review prompt and conference templates (`conferences/*.json`, one per venue).
  - `config.py`: settings from `SIBYL_*` env vars or `backend/.env`; document new ones in `backend/.env.example`.
- `backend/tests/`: pytest, mirroring `src/sibyl/` (`tests/services/`, `tests/routers/`, …). `tests/inference/fake_vllm.py` stands in for a vLLM server.
- `web/`: Next.js app (App Router). One route per page in `src/app/` (`review`, `library`, `models`, `gpu`); the root layout holds the shell and `providers.tsx`.
  - `src/features/<page>/`: that page's components, hooks and context. A feature imports from `components/`, `hooks/` and `lib/`, never from another feature; pages compose features.
  - `src/components/`: components shared by features; shadcn-style primitives in `ui/` (dialog, alert, spinner, native select, …).
  - Server data goes through TanStack Query: every read is defined once in `src/lib/api/queries.ts`, and changes invalidate the keys in `invalidates`. Don't fetch in `useEffect`.
  - Vitest tests in `src/__tests__/`, mirroring `src/`; `helpers/` has `renderWithQuery`, `mockApi` (route-based fetch stub) and `FakeWebSocket`.
- API contract: every backend route returns a pydantic model from `schemas/`. `web/openapi.json` and `web/src/lib/api/schema.d.ts` are generated from them; never edit either by hand. After changing a route or response model, run `npm run gen:api` in `web/` and commit both files (CI fails otherwise). The web app calls the backend only through `api` in `src/lib/api/index.ts`; `src/lib/types.ts` aliases the generated types.
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
