"""Sibyl: An LLM-powered research paper review system."""

import logging
import os
from contextlib import asynccontextmanager
from typing import cast

import click
import uvicorn
from decima.logger import CustomLogger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sibyl.ollama_clients import _is_docker, base_ollama, docker_ollama
from sibyl.routers import web_gpu, web_reviews, web_upload, web_ws

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

CustomLogger.setup_logging("logs", "app", level="DEBUG", class_length=30)
logger: CustomLogger = cast("CustomLogger", logging.getLogger("sibyl.main"))
logger.info("Starting Sibyl application...")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, D103
    logger.info("Starting up: Initializing resources...")

    if _is_docker():
        logger.info("Running in Docker environment. Using internal Ollama host.")
        app.state.ollama_clients = docker_ollama
    else:
        app.state.ollama_clients = {0: base_ollama}

    yield

    logger.info("Shutting down: Cleaning up...")


app = FastAPI(
    title="Sibyl Research Paper Review System",
    description="AI-powered research paper review using local LLMs",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,  # type: ignore[invalid-argument-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(web_upload.router, prefix="/api", tags=["Upload"])
app.include_router(web_ws.router, prefix="/ws", tags=["WebSocket"])
app.include_router(web_gpu.router, prefix="/api", tags=["GPU"])


@app.get("/")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "online", "system": "Sibyl"}


@click.command()
@click.option("--host", default="0.0.0.0", type=str)  # noqa: S104
@click.option("--port", default=8000, type=int)
@click.option("--ssl-certfile", default=None, type=str, help="Path to SSL certificate file for HTTPS")
@click.option("--ssl-keyfile", default=None, type=str, help="Path to SSL key file for HTTPS")
@click.option("--log-level", required=True, type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=True))
def run_server(host: str, port: int, ssl_certfile: str | None, ssl_keyfile: str | None, log_level: str) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to bind to
        ssl_certfile: Path to SSL certificate file
        ssl_keyfile: Path to SSL key file
        log_level: Logging level (TRACE, DEBUG, INFO, WARNING, ERROR)

    """
    logger: CustomLogger = cast("CustomLogger", logging.getLogger("sibyl.main"))
    logger.info(f"Starting Sibyl server on {host}:{port} with log level {log_level}")

    uvicorn.run(app, host=host, port=port, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile, log_config=None, log_level=log_level.lower())


if __name__ == "__main__":
    run_server()
