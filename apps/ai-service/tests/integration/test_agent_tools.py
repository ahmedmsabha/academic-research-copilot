"""Integration tests for calculator, weather, and web-search tool routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.errors import ProviderTimeoutError
from app.providers.llm import FakeLLMProvider
from app.providers.search import FakeWebSearchProvider, WebSearchHit
from app.providers.weather import FakeWeatherProvider
from tests.fixtures.pdfs import make_text_pdf


def _bootstrap_conversation(client: TestClient, headers: dict[str, str]) -> str:
    project = client.post("/api/v1/projects", json={"name": "Agent Project"}, headers=headers)
    assert project.status_code == 201
    project_id = project.json()["id"]
    conversation = client.post(
        f"/api/v1/projects/{project_id}/conversations",
        json={"title": "Agent chat"},
        headers=headers,
    )
    assert conversation.status_code == 201
    return conversation.json()["id"]


def test_calculator_route(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_llm: FakeLLMProvider,
) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)
    calls_before = len(fake_llm.calls)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What is 12 * (3 + 4)?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "calculator"
    assert payload["status"] == "Using calculator"
    assert "84" in payload["assistant_message"]["content"]
    assert "calculator" in payload["assistant_message"]["content"].lower()
    assert payload["citations"] == []
    assert payload["web_sources"] == []
    assert len(fake_llm.calls) == calls_before


def test_calculator_division_by_zero_is_user_safe(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "calculate 10 / 0"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "calculator"
    assert "zero" in payload["assistant_message"]["content"].lower()


def test_weather_route(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_weather: FakeWeatherProvider,
) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What's the weather in Paris?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "weather"
    assert payload["status"] == "Checking weather"
    content = payload["assistant_message"]["content"]
    assert "external weather tool" in content.lower()
    assert "Paris" in content
    assert "18.0" in content or "18" in content
    assert fake_weather.calls
    assert fake_weather.calls[0][0] == "Paris"
    assert payload["citations"] == []


def test_weather_country_now_is_resolved(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_weather: FakeWeatherProvider,
) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What is the weather in Ireland now?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "weather"
    content = payload["assistant_message"]["content"].lower()
    assert "couldn't resolve" not in content
    assert "external weather tool" in content
    attempted = [location for location, _when in fake_weather.calls]
    assert attempted
    assert all(" now" not in location.lower() for location in attempted)


def test_weather_needs_location(client: TestClient, auth_headers: dict[str, str]) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What's the weather?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "weather"
    assert "location" in payload["assistant_message"]["content"].lower()


def test_web_search_route(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_web_search: FakeWebSearchProvider,
    fake_llm: FakeLLMProvider,
) -> None:
    fake_llm.reply = (
        "This answer uses an external web search. Python 3.13 includes performance improvements."
    )
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Search the web for the latest Python release"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "web_search"
    assert payload["status"] == "Searching the web"
    assert payload["web_sources"]
    assert payload["web_sources"][0]["url"].startswith("https://")
    assert payload["web_sources"][0]["provider"] == "fake-search"
    assert payload["citations"] == []
    assert "external web search" in payload["assistant_message"]["content"].lower()
    assert fake_web_search.calls
    assert "latest Python release" in fake_web_search.calls[0]


def test_web_search_retries_when_first_query_is_empty(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_llm: FakeLLMProvider,
) -> None:
    fake_llm.reply = (
        "This answer uses an external web search. "
        "American films are often used by English learners."
    )
    client.app.state.web_search_provider = FakeWebSearchProvider(
        misses={"american movies to improve english"},
        hits=[
            WebSearchHit(
                title="Best American movies to learn English",
                url="https://example.com/learn-english-movies",
                snippet="Watch American films with subtitles to improve English listening.",
                provider="fake-search",
                retrieved_at=FakeWebSearchProvider().hits[0].retrieved_at,
            )
        ],
    )
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Search the web for American movies to improve English"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "web_search"
    assert payload["web_sources"]
    assert "didn't find usable results" not in payload["assistant_message"]["content"].lower()


def test_web_search_timeout_is_user_safe(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    class TimeoutSearch(FakeWebSearchProvider):
        async def search(self, *, query: str, max_results: int = 5):  # type: ignore[no-untyped-def]
            raise ProviderTimeoutError("Web search timed out. Please try again.")

    client.app.state.web_search_provider = TimeoutSearch()
    conversation_id = _bootstrap_conversation(client, auth_headers)
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Search the web for academic citations"},
        headers=auth_headers,
    )
    assert send.status_code == 504
    body = send.json()
    assert body["error"]["code"] == "PROVIDER_TIMEOUT"
    assert "Traceback" not in body["error"]["message"]


def test_calculator_still_wins_when_documents_are_ready(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post("/api/v1/projects", json={"name": "Mixed"}, headers=auth_headers)
    project_id = project.json()["id"]
    pdf = make_text_pdf("Neural embeddings map text to vectors for semantic search.")
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("notes.pdf", pdf, "application/pdf")},
    )
    assert upload.json()["status"] == "ready"
    conversation = client.post(
        f"/api/v1/projects/{project_id}/conversations",
        json={"title": "Mixed chat"},
        headers=auth_headers,
    )
    conversation_id = conversation.json()["id"]
    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What is 25 * 4?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "calculator"
    assert "100" in payload["assistant_message"]["content"]
    assert payload["citations"] == []
