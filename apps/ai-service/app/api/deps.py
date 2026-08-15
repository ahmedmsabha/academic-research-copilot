"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.providers.embeddings import (
    EmbeddingProvider,
    FakeEmbeddingProvider,
    GeminiEmbeddingProvider,
)
from app.providers.llm import FakeLLMProvider, GeminiLLMProvider, LLMProvider
from app.providers.search import (
    DuckDuckGoHtmlSearchProvider,
    DuckDuckGoSearchProvider,
    FakeWebSearchProvider,
    FallbackWebSearchProvider,
    GeminiSearchProvider,
    TavilySearchProvider,
    WebSearchProvider,
)
from app.providers.storage import LocalObjectStorage, ObjectStorage
from app.providers.weather import FakeWeatherProvider, OpenMeteoWeatherProvider, WeatherProvider
from app.repositories.memory_store import MemoryStore, get_store
from app.repositories.postgres_store import PostgresStore
from app.services.chat import ChatService
from app.services.documents import DocumentService
from app.services.projects import ProjectService
from app.services.prompt_lab import PromptLabService

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


@lru_cache
def _build_default_embeddings() -> EmbeddingProvider:
    settings = get_settings()
    if settings.app_env == "test" or settings.dev_fake_embeddings:
        return FakeEmbeddingProvider(dimension=settings.embedding_dimension)
    return GeminiEmbeddingProvider(
        api_key=settings.resolved_llm_api_key,
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
        timeout_ms=settings.embedding_timeout_ms,
        batch_size=settings.embedding_batch_size,
        batch_pause_ms=settings.embedding_batch_pause_ms,
    )


@lru_cache
def _build_default_storage() -> ObjectStorage:
    settings = get_settings()
    return LocalObjectStorage(settings.storage_root_path)


@lru_cache
def _build_default_weather() -> WeatherProvider:
    settings = get_settings()
    if settings.app_env == "test":
        return FakeWeatherProvider()
    return OpenMeteoWeatherProvider(timeout_ms=settings.weather_timeout_ms)


@lru_cache
def _build_default_web_search() -> WebSearchProvider:
    settings = get_settings()
    if settings.app_env == "test":
        return FakeWebSearchProvider()
    providers: list[WebSearchProvider] = []
    if settings.web_search_api_key:
        providers.append(
            TavilySearchProvider(
                api_key=settings.web_search_api_key,
                timeout_ms=settings.web_search_timeout_ms,
            )
        )
    providers.append(DuckDuckGoHtmlSearchProvider(timeout_ms=settings.web_search_timeout_ms))
    providers.append(DuckDuckGoSearchProvider(timeout_ms=settings.web_search_timeout_ms))
    if settings.resolved_llm_api_key and not settings.dev_fake_llm:
        providers.append(
            GeminiSearchProvider(
                api_key=settings.resolved_llm_api_key,
                model=settings.web_search_gemini_model,
                timeout_ms=max(settings.web_search_timeout_ms, settings.llm_timeout_ms),
            )
        )
    if len(providers) == 1:
        return providers[0]
    return FallbackWebSearchProvider(*providers)


def get_llm_provider(request: Request) -> LLMProvider:
    override = getattr(request.app.state, "llm_provider", None)
    if override is not None:
        return override  # type: ignore[no-any-return]
    return _build_default_llm()


def get_embedding_provider(request: Request) -> EmbeddingProvider:
    override = getattr(request.app.state, "embedding_provider", None)
    if override is not None:
        return override  # type: ignore[no-any-return]
    return _build_default_embeddings()


def get_object_storage(request: Request) -> ObjectStorage:
    override = getattr(request.app.state, "object_storage", None)
    if override is not None:
        return override  # type: ignore[no-any-return]
    return _build_default_storage()


def get_weather_provider(request: Request) -> WeatherProvider:
    override = getattr(request.app.state, "weather_provider", None)
    if override is not None:
        return override  # type: ignore[no-any-return]
    return _build_default_weather()


def get_web_search_provider(request: Request) -> WebSearchProvider:
    override = getattr(request.app.state, "web_search_provider", None)
    if override is not None:
        return override  # type: ignore[no-any-return]
    return _build_default_web_search()


def get_project_service(store: Store = Depends(get_app_store)) -> ProjectService:
    return ProjectService(store)  # type: ignore[arg-type]


def get_chat_service(
    request: Request,
    store: Store = Depends(get_app_store),
    llm: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
    weather: WeatherProvider = Depends(get_weather_provider),
    web_search: WebSearchProvider = Depends(get_web_search_provider),
) -> ChatService:
    # Do not resolve embeddings during dependency injection for every chat request.
    # Task 1 (llm) must keep working even if embedding setup is mid-change or broken.
    override = getattr(request.app.state, "embedding_provider", None)

    def embeddings_factory() -> EmbeddingProvider:
        if override is not None:
            return override  # type: ignore[no-any-return]
        return _build_default_embeddings()

    return ChatService(
        store=store,
        llm=llm,
        settings=settings,
        embeddings=override if override is not None else None,
        embeddings_factory=None if override is not None else embeddings_factory,
        weather=weather,
        web_search=web_search,
    )


def get_document_service(
    store: Store = Depends(get_app_store),
    storage: ObjectStorage = Depends(get_object_storage),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(
        store=store,
        storage=storage,
        embeddings=embeddings,
        settings=settings,
    )


def get_prompt_lab_service(
    store: Store = Depends(get_app_store),
    llm: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
) -> PromptLabService:
    return PromptLabService(store=store, llm=llm, settings=settings)
