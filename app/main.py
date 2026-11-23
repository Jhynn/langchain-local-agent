from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request, Response
from app.api.endpoints import chat
from app.core.database import db, init_database
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting up application and initializing MariaDB...")
    init_database()
    yield
    logger.info("Shutting down application and closing MariaDB connection...")
    if not db.is_closed():
        db.close()


app: FastAPI = FastAPI(
    title="LangGraph Corporate Agent API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
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


app.include_router(chat.router, prefix="/api/chat", tags=["Agent Chat"])