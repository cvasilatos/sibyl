FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY README.md .
COPY src/ src/

RUN curl -o install-uv.sh -LsSf https://astral.sh/uv/install.sh
RUN chmod +x install-uv.sh
RUN sh install-uv.sh
ENV PATH="/root/.local/bin:$PATH"
RUN uv sync --extra web --extra dev
RUN uv build

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

EXPOSE 8000

CMD ["sibyl", "web", "--host", "0.0.0.0", "--port", "8000"]
