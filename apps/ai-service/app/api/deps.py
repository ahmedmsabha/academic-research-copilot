"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.providers.llm import FakeLLMProvider, GeminiLLMProvider, LLMProvider
from app.repositories.memory_store import MemoryStore, get_store
from app.repositories.postgres_store import PostgresStore
from app.services.chat import ChatService
from app.services.projects import ProjectService

Store = MemoryStore | PostgresStore


def get_db() -> Generator[Session | None, None, None]:
    settings = get_settings()
    if settings.app_env == "test" or not settings.database_url:
        yield None
        return

    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_app_store(db: Session | None = Depends(get_db)) -> Store:
    if db is not None:
        return PostgresStore(db)
    return get_store()


@lru_cache
def _build_default_llm() -> LLMProvider:
    settings = get_settings()
    if settings.app_env == "test" or settings.dev_fake_llm:
        return FakeLLMProvider(
            reply=(
                "Retrieval-augmented generation (RAG) looks up relevant passages from your "
                "documents before answering, instead of relying only on model memory. "
                "That helps student answers stay grounded in the assigned reading."
            )
        )
    return GeminiLLMProvider(
        api_key=settings.resolved_llm_api_key,
        default_model=settings.llm_model,
        timeout_ms=settings.llm_timeout_ms,
    )


def get_llm_provider(request: Request) -> LLMProvider:
    override = getattr(request.app.state, "llm_provider", None)
    if override is not None:
        return override  # type: ignore[no-any-return]
    return _build_default_llm()


def get_project_service(store: Store = Depends(get_app_store)) -> ProjectService:
    return ProjectService(store)  # type: ignore[arg-type]


def get_chat_service(
    store: Store = Depends(get_app_store),
    llm: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    return ChatService(store=store, llm=llm, settings=settings)  # type: ignore[arg-type]
