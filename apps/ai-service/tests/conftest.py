"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Ensure settings load in test mode before app import side effects.
os.environ["APP_ENV"] = "test"
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("LLM_MODEL", "gemini-2.0-flash")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.main import create_app  # noqa: E402
from app.providers.llm import FakeLLMProvider  # noqa: E402
from app.repositories.memory_store import reset_store  # noqa: E402


@pytest.fixture()
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider(reply="Hello from the fake model.")


@pytest.fixture()
def client(fake_llm: FakeLLMProvider):
    reset_store()
    app = create_app()
    app.state.llm_provider = fake_llm
    with TestClient(app) as test_client:
        yield test_client
    reset_store()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"X-User-Id": "test-user-1"}
