"""Integration tests for document upload and grounded RAG chat."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.providers.llm import FakeLLMProvider
from tests.fixtures.pdfs import make_text_pdf


def _bootstrap_project(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    project = client.post("/api/v1/projects", json={"name": "RAG Project"}, headers=headers)
    assert project.status_code == 201
    project_id = project.json()["id"]
    conversation = client.post(
        f"/api/v1/projects/{project_id}/conversations",
        json={"title": "Doc chat"},
        headers=headers,
    )
    assert conversation.status_code == 201
    return project_id, conversation.json()["id"]


def test_upload_indexes_and_lists_document(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, _ = _bootstrap_project(client, auth_headers)
    pdf = make_text_pdf(
        "Neural embeddings map text to vectors for semantic search.",
        page2="Cosine similarity ranks nearby passages.",
    )
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("embeddings-notes.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201
    document = upload.json()
    assert document["status"] == "ready"
    assert document["filename"] == "embeddings-notes.pdf"
    assert document["page_count"] == 2

    listed = client.get(f"/api/v1/projects/{project_id}/documents", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_rag_answer_includes_citation(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_llm: FakeLLMProvider,
) -> None:
    fake_llm.reply = "Embeddings map text to vectors for semantic search."
    project_id, conversation_id = _bootstrap_project(client, auth_headers)
    pdf = make_text_pdf(
        "Neural embeddings map text to vectors for semantic search in academic notes."
    )
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("notes.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201
    assert upload.json()["status"] == "ready"

    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What do neural embeddings map text to?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "rag"
    assert payload["status"] == "Searching uploaded documents"
    assert payload["citations"]
    assert payload["citations"][0]["filename"] == "notes.pdf"
    assert payload["citations"][0]["page_start"] == 1
    assert "notes.pdf, p. 1" in payload["citations"][0]["label"]
    assert fake_llm.calls
    prompt = fake_llm.calls[-1].messages[0].content
    assert "Document excerpts:" in prompt
    assert "neural embeddings" in prompt.lower()


def test_insufficient_evidence_is_honest(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, conversation_id = _bootstrap_project(client, auth_headers)
    pdf = make_text_pdf("Photosynthesis converts light energy into chemical energy in plants.")
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("bio.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201

    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What is the capital of Mars and the latest stock price of ACME?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "rag"
    assert payload["citations"] == []
    assert "do not contain enough information" in payload["assistant_message"]["content"].lower()


def test_overview_summary_uses_document_chunks(
    client: TestClient,
    auth_headers: dict[str, str],
    fake_llm: FakeLLMProvider,
) -> None:
    fake_llm.reply = "The paper explains how neural embeddings support semantic search."
    project_id, conversation_id = _bootstrap_project(client, auth_headers)
    pdf = make_text_pdf(
        "Neural embeddings map text to vectors for semantic search in academic notes."
    )
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("notes.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201
    assert upload.json()["status"] == "ready"

    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Summarize the research attached", "mode": "rag"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    payload = send.json()
    assert payload["route"] == "rag"
    assert payload["citations"]
    assert payload["citations"][0]["filename"] == "notes.pdf"
    assert any(c.get("page_start") == 1 for c in payload["citations"])
    assert "do not contain enough information" not in payload["assistant_message"]["content"].lower()
    prompt = fake_llm.calls[-1].messages[0].content
    assert "Document excerpts:" in prompt
    assert "neural embeddings" in prompt.lower()
    assert "abstract" in prompt.lower() or "concise grounded summary" in prompt.lower()


def test_reject_non_pdf(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id, _ = _bootstrap_project(client, auth_headers)
    response = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_DOCUMENT"


def test_document_isolation(client: TestClient) -> None:
    user_a = {"X-User-Id": "doc-alice"}
    user_b = {"X-User-Id": "doc-bob"}
    project_id, _ = _bootstrap_project(client, user_a)
    pdf = make_text_pdf("Private project document about quantum tunneling.")
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=user_a,
        files={"file": ("private.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    forbidden = client.get(
        f"/api/v1/projects/{project_id}/documents/{document_id}",
        headers=user_b,
    )
    assert forbidden.status_code == 404


def test_delete_removes_from_retrieval(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    project_id, conversation_id = _bootstrap_project(client, auth_headers)
    pdf = make_text_pdf("Graphene is a single layer of carbon atoms arranged in a lattice.")
    upload = client.post(
        f"/api/v1/projects/{project_id}/documents",
        headers=auth_headers,
        files={"file": ("materials.pdf", pdf, "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]

    deleted = client.delete(
        f"/api/v1/projects/{project_id}/documents/{document_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204

    send = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "What is graphene?"},
        headers=auth_headers,
    )
    assert send.status_code == 201
    # No ready documents remain, so chat falls back to direct LLM route.
    assert send.json()["route"] == "llm"
