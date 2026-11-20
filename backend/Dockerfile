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


EXPOSE 8000


CMD ["sibyl", "--host", "0.0.0.0", "--port", "8000", "--log-level", "INFO"]
