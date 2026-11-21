# Sibyl – Copilot Coding Agent Instructions

## What This Repository Does

Sibyl is an LLM-powered research paper review system. It uses local open-source AI models (via Ollama) to extract text from PDF research papers, generate structured reviews, and provide comparative analysis. The repository has two self-contained sub-projects:

- `backend/` – Python 3.12 / FastAPI REST + WebSocket server (the main source of logic)
- `web/` – Next.js 16 / React 19 / TypeScript frontend

The full stack is run with Docker Compose (`docker-compose.yml` at repo root). For development, each sub-project runs independently.

---

## Backend (`backend/`)

**Runtime:** Python 3.12 (see `backend/.python-version`)  
**Package manager:** `uv` (required – do NOT use `pip install` directly)  
**Build tool:** Hatchling via `pyproject.toml`  
**Linter/Formatter:** Ruff  
**Type checker:** `ty` (from Astral)  
**Test runner:** pytest

### Key Files

- `backend/pyproject.toml` – all project config: dependencies, Ruff rules, pytest settings, `ty` config
- `backend/src/sibyl/` – all Python source code
  - `main.py` – FastAPI app + server entry point (`sibyl` command)
  - `config.py` – `SibylConfig` and `LLMConfig` Pydantic models; `MAX_SCORE = 5`
  - `state.py` – shared app state (review sessions, storage)
  - `routers/` – FastAPI route handlers (`conferences.py`, `gpu.py`, `reviews.py`, `upload.py`, `ws.py`)
  - `schemas/` – Pydantic models for HTTP request/response
  - `services/` – review pipeline: `reviewer.py`, `comparison.py`, `pdf_parser.py`, `figures.py`, `conferences.py`, `hardware.py`, `model_catalog.py`
  - `inference/` – pluggable engines (Ollama, vLLM, OpenAI-compatible)
  - `storage/` – Review storage engine
  - `resources/` – review prompt and conference templates
- `backend/tests/` – pytest test suite, mirroring `src/sibyl/`
- `backend/.env.example` – environment variable template (copy to `backend/.env`)

### Setup and Build (Always Follow This Order)

```bash
cd backend

# 1. Install dependencies (required before any other command)
uv sync --extra dev --extra web

# 2. Copy env file if needed
cp .env.example .env   # edit OLLAMA_MODEL=llama3.2 etc.
```

### Running Tests

```bash
cd backend
uv run pytest
# Or without coverage for speed:
uv run pytest --no-cov
```

**⚠ Known pre-existing test failures (not caused by your changes):**
- `test_comparison.py` and several `test_reviewer.py` / `test_storage.py` tests fail with `ValidationError: score must be <= 5` — tests use score values of 7–9 but `MAX_SCORE = 5` in `config.py`.
- `test_config.py::test_llm_config_defaults` fails because the actual `max_tokens` default is `300000`, not `8000`.
- `test_reviewer.py` tests referencing `_parse_review_response` fail (method doesn't exist on `ReviewSystem`).
- 32 tests pass; do not break them.

### Linting and Formatting

```bash
cd backend
# Check linting (must pass with no errors)
uv run ruff check src/

# Format check
uv run ruff format --check src/

# Apply formatting
uv run ruff format src/

# Type checking
uv run ty check src/
```

Ruff is configured in `pyproject.toml` (`[tool.ruff]`): `line-length = 180`, target Python 3.12, `src = ["./src"]`. All `ALL` rules enabled with specific ignores listed there.

### Pre-commit Hooks

```bash
cd backend
uv run pre-commit run --all-files
```

Hooks run: `ruff-check`, `ruff-format`, `uv-lock` (checks `uv.lock` is up to date), `ty check`.

---

## Frontend (`web/`)

**Runtime:** Node.js 18+ (v24 confirmed working)  
**Framework:** Next.js 16.1.6, React 19, TypeScript 5  
**Linter/Formatter:** Biome (NOT ESLint) — configured in `web/biome.json`  
**No frontend test suite exists.**

### Key Files

- `web/package.json` – scripts: `dev`, `build`, `start`, `lint`, `format`, `check`
- `web/biome.json` – Biome linting/formatting config (line width 180, double quotes, space indent)
- `web/tsconfig.json` – TypeScript config; path alias `@/*` → `./src/*`
- `web/next.config.ts` – Next.js config (minimal)
- `web/src/app/page.tsx` – main page component
- `web/src/app/layout.tsx` – root layout
- `web/src/lib/config.ts` – API URL config (`NEXT_PUBLIC_API_URL`, default `http://localhost:8000`)
- `web/src/components/` – React components
- `web/.env.local.example` – env template; create `web/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`

### Setup and Build

```bash
cd web

# 1. Always install dependencies first
npm install

# 2. Build for production (validates TypeScript)
npm run build

# 3. Development server
npm run dev   # http://localhost:3000
```

### Linting and Formatting

```bash
cd web
npm run lint      # biome lint
npm run format    # biome format --write
npm run check     # biome check --write (lint + format combined)
```

**⚠ Known pre-existing lint issues:** `npm run lint` reports ~18 errors and ~9 warnings in existing code. Do not introduce new Biome errors. The production build (`npm run build`) succeeds despite lint errors.

---

## No CI Workflows

There are no GitHub Actions workflows in this repository. Validation is done locally via pre-commit hooks (backend only).

## Docker / Full Stack

```bash
# From repo root:
cp backend/.env.example backend/.env
docker compose up -d
docker compose exec ollama ollama pull llama3.2
# App at http://localhost:4000
```

Services: `ollama` (port 21434), `grobid` (8070), `backend` (8000), `web` (4000→3000).

## Architecture Notes

- `MAX_SCORE = 5` is defined in `backend/src/sibyl/config.py` and enforced as a Pydantic validator on `ReviewCriteria.score`.
- The `decimalog` dependency is sourced from a private Git repo (`github.com/cvasilatos/decimalog`); it is referenced in `uv.lock` and installed by `uv sync`.
- Storage artifacts are saved to `sibyl_storage/` (gitignored) and logs to `logs/` (gitignored).
- The frontend API URL is configured via `NEXT_PUBLIC_API_URL` env var (default: `http://localhost:8000`).

## Trust These Instructions

Trust this document as the primary source of truth. Only search the codebase if information here appears incomplete or incorrect.
