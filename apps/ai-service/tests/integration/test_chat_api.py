"""Integration tests for Task 1 chat APIs (fake LLM, no live Gemini)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.providers.llm import FakeLLMProvider


def _bootstrap_conversation(client: TestClient, headers: dict[str, str]) -> str:
    project = client.post("/api/v1/projects", json={"name": "My Research Project"}, headers=headers)
    assert project.status_code == 201
    project_id = project.json()["id"]

    conversation = client.post(
        f"/api/v1/projects/{project_id}/conversations",
        json={"title": "Demo chat"},
        headers=headers,
    )
    assert conversation.status_code == 201
    return conversation.json()["id"]


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_alias_and_index(client: TestClient) -> None:
    alias = client.get("/api/health")
    assert alias.status_code == 200
    assert alias.json() == {"status": "ok", "service": "ai-service"}

    index = client.get("/api")
    assert index.status_code == 200
    assert index.json()["api"] == "/api/v1"


def test_requires_user_header(client: TestClient) -> None:
    response = client.post("/api/v1/projects", json={"name": "My Research Project"})
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "stack" not in body["error"]["message"].lower()


def test_send_message_and_list_history(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_llm: FakeLLMProvider,
) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)

    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Explain embeddings briefly."},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "llm"
    assert payload["status"] == "Generating response"
    assert payload["assistant_message"]["content"] == "Hello from the fake model."
    assert payload["assistant_message"]["provider"] == "fake"
    assert len(fake_llm.calls) >= 1

    history = client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers,
    )
    assert history.status_code == 200
    messages = history.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_blank_message_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    conversation_id = _bootstrap_conversation(client, auth_headers)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in body["error"]


def test_list_conversations_is_owner_scoped(client: TestClient) -> None:
    user_a = {"X-User-Id": "alice"}
    user_b = {"X-User-Id": "bob"}

    project_a = client.post(
        "/api/v1/projects",
        json={"name": "My Research Project"},
        headers=user_a,
    )
    assert project_a.status_code == 201
    project_id = project_a.json()["id"]

    created = client.post(
        f"/api/v1/projects/{project_id}/conversations",
        json={"title": "Alice notes"},
        headers=user_a,
    )
    assert created.status_code == 201

    listed = client.get(f"/api/v1/projects/{project_id}/conversations", headers=user_a)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["title"] == "Alice notes"

    hidden = client.get(f"/api/v1/projects/{project_id}/conversations", headers=user_b)
    assert hidden.status_code == 404


def test_first_message_retitles_default_conversation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project = client.post(
        "/api/v1/projects",
        json={"name": "My Research Project"},
        headers=auth_headers,
    )
    project_id = project.json()["id"]
    conversation = client.post(
        f"/api/v1/projects/{project_id}/conversations",
        json={"title": "New chat"},
        headers=auth_headers,
    )
    conversation_id = conversation.json()["id"]

    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What is 12 * (3 + 4)?"},
        headers=auth_headers,
    )
    assert send.status_code == 201

    listed = client.get(f"/api/v1/projects/{project_id}/conversations", headers=auth_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "What is 12 * (3 + 4)?"


def test_project_isolation(client: TestClient) -> None:
    user_a = {"X-User-Id": "alice"}
    user_b = {"X-User-Id": "bob"}

    conversation_id = _bootstrap_conversation(client, user_a)
    forbidden = client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=user_b,
    )
    assert forbidden.status_code == 404


def test_provider_failure_is_user_safe(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    class BoomLLM(FakeLLMProvider):
        async def generate(self, request):  # type: ignore[no-untyped-def]
            from app.core.errors import ProviderUnavailableError

            raise ProviderUnavailableError()

    client.app.state.llm_provider = BoomLLM()
    conversation_id = _bootstrap_conversation(client, auth_headers)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Hello"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "Traceback" not in body["error"]["message"]
