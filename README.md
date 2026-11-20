# Sibyl 🔮

An LLM-powered research paper review system that leverages local open-source AI models to provide comprehensive, comparative reviews of academic papers.

## Repository Structure

This repository is organized into two self-contained sub-projects:

| Directory | Description |
|-----------|-------------|
| [`backend/`](./backend/) | Python / FastAPI API server |
| [`web/`](./web/) | Next.js frontend |

Each sub-directory contains its own `README.md`, `Dockerfile`, and all files needed to develop, test, and deploy that component independently.

## Quick Start (Docker Compose)

The easiest way to run the full stack is with Docker Compose from the repository root:

```bash
# 1. Copy and edit the backend environment file
cp backend/.env.example backend/.env

# 2. Start all services (Ollama, GROBID, backend, frontend)
docker compose up -d

# 3. Pull a model into Ollama (first time only)
docker compose exec ollama ollama pull llama3.2

# 4. Open the web app
#    http://localhost:4000
```

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
