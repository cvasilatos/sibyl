import contextlib
import logging
from typing import TYPE_CHECKING, cast

from decima.logger import CustomLogger
from fastapi import APIRouter, Query, WebSocket

from sibyl.routers.auth import connection_user
from sibyl.schemas.ws import PullProgress, SocketError

if TYPE_CHECKING:
    from sibyl.inference import InferenceEngine

router = APIRouter()


logger: CustomLogger = cast("CustomLogger", logging.getLogger(__name__))


@router.websocket("/pull")
async def pull_model(websocket: WebSocket, model_name: str = Query()) -> None:
    """WebSocket endpoint streaming model download progress from the active engine."""
    await websocket.accept()
    user = connection_user(websocket)
    if user is None:
        await websocket.send_json(SocketError(message="Sign in to download models").model_dump())
        await websocket.close(code=1008)
        return

    try:
        engine: InferenceEngine = websocket.app.state.engine
        logger.info(f"{user.username} is downloading model {model_name}")
        async for part in engine.pull(model_name):  # progress goes to the client only: a log line per chunk fills the disk
            await websocket.send_json(PullProgress.model_validate(part).model_dump())
        logger.info(f"Downloaded model {model_name}")

    except Exception as e:
        logger.exception(f"Error during model pull for {model_name}")
        await websocket.send_json(SocketError(message=str(e)).model_dump())
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
