"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure settings load in test mode before app import side effects.
os.environ["APP_ENV"] = "test"
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("LLM_MODEL", "gemini-flash-lite-latest")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DEV_FAKE_EMBEDDINGS", "true")
os.environ.setdefault("EMBEDDING_DIMENSION", "64")
os.environ.setdefault("RETRIEVAL_MAX_DISTANCE", "0.85")
os.environ["STORAGE_LOCAL_ROOT"] = str(Path(__file__).resolve().parent / ".tmp-uploads")

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.providers.embeddings import FakeEmbeddingProvider  # noqa: E402
from app.providers.llm import FakeLLMProvider  # noqa: E402
from app.providers.storage import LocalObjectStorage  # noqa: E402
from app.repositories.memory_store import reset_store  # noqa: E402

get_settings.cache_clear()


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider(reply="Hello from the fake model.")


@pytest.fixture()
def fake_embeddings() -> FakeEmbeddingProvider:
    settings = get_settings()
    return FakeEmbeddingProvider(dimension=settings.embedding_dimension)


@pytest.fixture()
def client(fake_llm: FakeLLMProvider, fake_embeddings: FakeEmbeddingProvider, tmp_path: Path):
    reset_store()
    get_settings.cache_clear()
    settings = get_settings()
    storage_root = tmp_path / "uploads"
    app = create_app()
    app.state.llm_provider = fake_llm
    app.state.embedding_provider = fake_embeddings
    app.state.object_storage = LocalObjectStorage(storage_root)
    # Keep settings aligned with the temporary storage used by background helpers.
    object.__setattr__(settings, "storage_local_root", str(storage_root))
    with TestClient(app) as test_client:
        yield test_client
    reset_store()
    get_settings.cache_clear()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"X-User-Id": "test-user-1"}
