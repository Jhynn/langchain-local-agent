import time

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from collections.abc import AsyncGenerator, Awaitable, Callable

from app.core.logger import logger
from app.api.endpoints import chat
from app.api.endpoints import adk_chat, chat
from app.core.database import db, init_database
from app.agents.assistant_agent import assistant_agent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up application and initializing MariaDB...")
    init_database()
    yield
    logger.info("Shutting down application...")

    if not db.is_closed():
        db.close()

    assistant_agent.close()


api: FastAPI = FastAPI(
    title="LangGraph Corporate Agent API",
    version="1.0.0",
    lifespan=lifespan,
)


@api.middleware("http")
async def log_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    start_time: float = time.time()
    response: Response = await call_next(request)
    latency: float = time.time() - start_time
    logger.info(
        f"Method={request.method} Path={request.url.path} "
        f"Status={response.status_code} Latency={latency:.4f}s"
    )
    return response


api.include_router(chat.router, prefix="/api/chat", tags=["Agent Chat"])
api.include_router(adk_chat.router, prefix="/api/adk/chat", tags=["Google ADK Agent"])
