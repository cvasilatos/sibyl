ARG OLLAMA_VERSION=latest
FROM ollama/ollama:${OLLAMA_VERSION} AS ollama

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git\
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"
ENV PATH="/root/.cargo/bin:${PATH}"
ENV PATH="/app/.venv/bin:${PATH}"
ENV DATALAB_CACHE_DIR=/root/.cache/datalab

COPY pyproject.toml .
COPY README.md .
COPY src/ src/

RUN uv sync --all-groups
RUN uv build

RUN python -c "from marker.models import create_model_dict; create_model_dict()"

# Optional vLLM engine (SIBYL_ENGINE=vllm). Installed as an isolated uv tool so its pinned torch/CUDA
# versions never conflict with Marker's. Build with: --build-arg INSTALL_VLLM=true
ARG INSTALL_VLLM=false
ARG VLLM_VERSION=0.11.0
RUN if [ "$INSTALL_VLLM" = "true" ]; then uv tool install "vllm==${VLLM_VERSION}"; fi

# Ollama binary and its CUDA runtime, so the backend can start one `ollama serve` per GPU it detects
# (see sibyl.inference.ollama_gpus). Same image as the compose `ollama` service.
COPY --from=ollama /usr/bin/ollama /usr/bin/ollama
COPY --from=ollama /usr/lib/ollama /usr/lib/ollama

EXPOSE 8000


CMD ["sibyl", "serve", "--host", "0.0.0.0", "--port", "8000", "--log-level", "INFO"]
