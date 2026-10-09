"""FastAPI application entrypoint."""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import app.models  # noqa: F401 - register all models on Base.metadata
from app.api.v1 import realtime, router as v1_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.core.rate_limit import rate_limiter
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.bootstrap import seed_roles_and_permissions
from app.services.seed import seed_demo_data

configure_logging()

_REQUEST_COUNT: dict[str, int] = {}
_STARTED_AT = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env in {"development", "test"}:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed_roles_and_permissions(db)
        if settings.seed_demo:
            await seed_demo_data(db)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug or settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.debug or settings.app_env != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable]
):
    request_id = uuid.uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.4f}"
    return response


@app.middleware("http")
async def rate_limit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable]
):
    if request.url.path.startswith(settings.api_prefix) or request.url.path.startswith("/api"):
        client = request.client.host if request.client else "unknown"
        if not await rate_limiter.is_allowed(f"rl:{client}"):
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests"}},
            )
    return await call_next(request)


@app.middleware("http")
async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable]
):
    response = await call_next(request)
    path = request.url.path
    _REQUEST_COUNT[path] = _REQUEST_COUNT.get(path, 0) + 1
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "detail": exc.detail}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed", "detail": exc.errors()}},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "database_error", "message": "Database error occurred"}},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Internal server error"}},
    )


@app.get("/healthz", include_in_schema=False)
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz() -> dict:
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    lines = [
        "# HELP app_uptime_seconds Application uptime in seconds",
        "# TYPE app_uptime_seconds gauge",
        f"app_uptime_seconds {time.time() - _STARTED_AT:.2f}",
        "# HELP app_requests_total Total requests per path",
        "# TYPE app_requests_total counter",
    ]
    for path, count in _REQUEST_COUNT.items():
        lines.append(f'app_requests_total{{path="{path}"}} {count}')
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")


app.include_router(v1_router.api_router, prefix=settings.api_prefix)
app.include_router(realtime.router)
