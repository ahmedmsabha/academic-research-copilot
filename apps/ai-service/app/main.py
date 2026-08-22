"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.documents import run_indexing_recovery_loop
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    recovery = asyncio.create_task(run_indexing_recovery_loop(settings))
    try:
        yield
    finally:
        recovery.cancel()
        try:
            await recovery
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_runtime()
    app = FastAPI(
        title="Academic Research Copilot AI Service",
        version="0.1.0",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"service": "ai-service", "health": "/health", "api": "/api/v1"}

    @app.get("/api")
    def api_index() -> dict[str, str]:
        return {"service": "ai-service", "health": "/health", "api": "/api/v1"}

    @app.get("/health")
    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "ai-service"}

    return app


app = create_app()
