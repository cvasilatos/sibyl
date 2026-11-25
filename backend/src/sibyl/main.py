"""Sibyl: An LLM-powered research paper review system."""

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, cast

from anyio import to_thread
from decima.logger import CustomLogger
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic.json_schema import models_json_schema

from sibyl import config
from sibyl.inference import create_engine
from sibyl.routers import auth, conferences, gpu, review_forms, review_jobs, reviews, system, ws
from sibyl.schemas.system import Online
from sibyl.schemas.ws import WS_MESSAGES
from sibyl.services import pdf_parser
from sibyl.services.figures import prefetch_vlm
from sibyl.services.gpu_activity import GpuActivity
from sibyl.services.review_queue import ReviewQueue
from sibyl.state import storage

LOG_DIR = Path("logs")
KEEP_LOG_FILES = 10
"""Log files of earlier runs to keep; older ones are deleted at startup."""
JSON_LOG_BYTES = 10 * 1024**2
"""Size at which the JSON log is rotated (one previous file is kept)."""
QUIET_LOGGERS = ("httpx", "httpcore", "urllib3", "filelock", "PIL", "multipart", "asyncio")
"""Libraries that log every request or file access below WARNING."""
UNLOGGED_PATHS = ("/api/gpu", "/api/review-jobs", "/api/auth/me")
"""Endpoints the web app polls; logging every successful read would fill the disk."""


class _DropPolledRequests(logging.Filter):
    """Drop uvicorn access-log lines for successful reads of ``UNLOGGED_PATHS``."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:  # noqa: PLR2004 (client, method, path, http version, status)
            _, method, path, _, status = args
            return not (method == "GET" and isinstance(status, int) and status < 400 and str(path).split("?", 1)[0].startswith(UNLOGGED_PATHS))  # noqa: PLR2004
        return True


def setup_logging() -> None:
    """Log at ``SIBYL_LOG_LEVEL`` (INFO by default), keep noisy libraries quiet and delete all but the newest log files."""
    CustomLogger.setup_logging(str(LOG_DIR), "app", level=os.getenv("SIBYL_LOG_LEVEL", "INFO").upper(), class_length=30)
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").addFilter(_DropPolledRequests())
    root = logging.getLogger()
    for handler in list(root.handlers):  # decima appends to one JSON log forever: cap it instead
        if isinstance(handler, logging.FileHandler) and handler.baseFilename.endswith(".jsonl"):
            rotating = RotatingFileHandler(handler.baseFilename, maxBytes=JSON_LOG_BYTES, backupCount=1)
            rotating.setFormatter(handler.formatter)
            rotating.setLevel(handler.level)
            root.removeHandler(handler)
            handler.close()
            root.addHandler(rotating)
    for old in sorted(LOG_DIR.glob("app-*.log"), reverse=True)[KEEP_LOG_FILES:]:
        with contextlib.suppress(OSError):
            old.unlink()


setup_logging()
logger: CustomLogger = cast("CustomLogger", logging.getLogger("sibyl.main"))
logger.info("Starting Sibyl application...")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, D103
    logger.info("Starting up: Initializing resources...")

    app.state.engine = create_engine()
    logger.info(f"Inference engine: {app.state.engine.label}")

    async def release_gpus() -> None:
        await app.state.engine.release_gpus()
        await to_thread.run_sync(pdf_parser.release_models)

    # Nothing runs on the GPUs until a review starts; once reviews stop, model servers and PDF models are released.
    app.state.gpu_activity = GpuActivity(release_gpus)

    # Reviews run in the background, one per GPU, whether or not anyone keeps the page open.
    app.state.review_queue = ReviewQueue(app.state.engine, storage, app.state.gpu_activity, config.STORAGE_PATH / "review_jobs", app.state.engine.review_gpus())
    app.state.review_queue.load()
    app.state.review_queue.dispatch()

    # Download the figure-describing vision model in the background; the server is usable meanwhile.
    vlm_task = asyncio.create_task(prefetch_vlm(app.state.engine))
    vlm_task.add_done_callback(lambda t: t.cancelled() or t.exception() is None or logger.error(f"Vision model prefetch failed: {t.exception()}"))

    yield

    logger.info("Shutting down: Cleaning up...")
    await app.state.review_queue.aclose()
    await app.state.gpu_activity.aclose()
    vlm_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await vlm_task
    await app.state.engine.aclose()


class SibylAPI(FastAPI):
    """FastAPI app whose OpenAPI schema also lists the WebSocket message models, which no HTTP route references."""

    def openapi(self) -> dict[str, Any]:  # noqa: D102
        if self.openapi_schema is None:
            schema = super().openapi()
            _, defs = models_json_schema([(model, "serialization") for model in WS_MESSAGES], ref_template="#/components/schemas/{model}")
            components = schema.setdefault("components", {}).setdefault("schemas", {})
            for name, definition in defs.get("$defs", {}).items():
                components.setdefault(name, definition)  # models shared with HTTP routes (ReviewCriteria) keep FastAPI's version
        return cast("dict[str, Any]", self.openapi_schema)


app = SibylAPI(
    title="Sibyl Research Paper Review System",
    description="AI-powered research paper review using local LLMs",
    version="0.1.0",
    lifespan=lifespan,
)


def cors_origins() -> list[str]:
    """Web app origins allowed to call the API with the session cookie (``SIBYL_CORS_ORIGINS``, comma separated)."""
    return [origin.strip().rstrip("/") for origin in os.getenv("SIBYL_CORS_ORIGINS", "").split(",") if origin.strip()]


# The session cookie is SameSite=Lax, so other sites never send it; without SIBYL_CORS_ORIGINS any origin on the same
# site (e.g. the web app on another port of this host) may call the API with it.
app.add_middleware(
    CORSMiddleware,  # type: ignore[invalid-argument-type]
    allow_origins=cors_origins(),
    allow_origin_regex=None if cors_origins() else ".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

signed_in = [Depends(auth.require_user)]
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"], dependencies=signed_in)
app.include_router(review_jobs.router, prefix="/api", tags=["Review Queue"], dependencies=signed_in)
app.include_router(ws.router, prefix="/ws", tags=["WebSocket"])  # checks the session itself: WebSockets cannot answer 401
app.include_router(gpu.router, prefix="/api", tags=["GPU"], dependencies=signed_in)
app.include_router(conferences.router, prefix="/api", tags=["Conferences"], dependencies=signed_in)
app.include_router(review_forms.router, prefix="/api", tags=["Review Forms"], dependencies=signed_in)


@app.get("/")
async def health_check() -> Online:
    """Health check endpoint."""
    return Online(status="online", system="Sibyl")
