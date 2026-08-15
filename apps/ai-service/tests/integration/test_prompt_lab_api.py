"""Integration tests for Prompt Lab APIs (fake LLM, no live Gemini)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.providers.llm import FakeLLMProvider, LLMRequest, LLMResponse


class StrategyAwareFakeLLM:
    provider_name = "fake"

    def __init__(self) -> None:
        self.calls: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
        if "Return ONLY a JSON object" in last_user:
            text = json.dumps(
                {
                    "answer": "RAG retrieves evidence before answering.",
                    "key_points": ["Uses uploaded or searched text", "Reduces unsupported claims"],
                    "confidence": "high",
                    "limitations": "Depends on retrieval quality.",
                }
            )
        elif "same style as the examples" in last_user:
            text = "Few-shot: RAG looks up passages before answering."
        elif "same style as the example" in last_user:
            text = "One-shot: RAG looks up passages before answering."
        elif "numbered working" in last_user:
            text = (
                "1. Define RAG as retrieve-then-generate.\n"
                "2. Contrast it with parametric memory only.\n"
                "Final answer: RAG grounds answers in retrieved text."
            )
        else:
            text = "Zero-shot: RAG retrieves relevant passages before answering."
        return LLMResponse(
            text=text,
            model=request.model,
            provider="fake",
            prompt_tokens=11,
            completion_tokens=22,
            total_tokens=33,
        )


def _bootstrap_project(client: TestClient, headers: dict[str, str]) -> str:
    project = client.post("/api/v1/projects", json={"name": "My Research Project"}, headers=headers)
    assert project.status_code == 201
    return str(project.json()["id"])


def test_prompt_library_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/prompt-library")
    assert response.status_code == 401


def test_prompt_library_lists_versioned_strategies(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/prompt-library", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["strategies"]]
    assert ids == [
        "zero_shot",
        "one_shot",
        "few_shot",
        "chain_of_thought",
        "structured",
    ]
    assert body["version"] == "prompt-lab-v1"
    assert "{{input}}" in body["strategies"][0]["user_template"]


def test_comparison_run_and_ratings(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.app.state.llm_provider = StrategyAwareFakeLLM()
    project_id = _bootstrap_project(client, auth_headers)
    question = "Why do researchers use retrieval-augmented generation?"

    created = client.post(
        f"/api/v1/projects/{project_id}/prompt-experiments",
        json={"input": question},
        headers=auth_headers,
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["input"] == question
    assert len(payload["results"]) == 5
    by_strategy = {item["strategy"]: item for item in payload["results"]}
    assert by_strategy["zero_shot"]["output"].startswith("Zero-shot:")
    assert by_strategy["one_shot"]["output"].startswith("One-shot:")
    assert by_strategy["few_shot"]["output"].startswith("Few-shot:")
    assert "Final answer:" in by_strategy["chain_of_thought"]["output"]
    assert "Key points:" in by_strategy["structured"]["output"]
    assert "scratchpad" not in by_strategy["structured"]["output"].lower()
    assert by_strategy["structured"]["total_tokens"] == 33
    assert by_strategy["structured"]["cost_usd"] is None
    experiment_id = by_strategy["zero_shot"]["id"]
    assert experiment_id

    listed = client.get(
        f"/api/v1/projects/{project_id}/prompt-experiments",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    assert listed.json()["runs"][0]["run_id"] == payload["run_id"]

    rated = client.patch(
        f"/api/v1/prompt-experiments/{experiment_id}",
        json={"rating_accuracy": 5, "rating_clarity": 4},
        headers=auth_headers,
    )
    assert rated.status_code == 200
    assert rated.json()["rating_accuracy"] == 5
    assert rated.json()["rating_clarity"] == 4


def test_blank_input_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    project_id = _bootstrap_project(client, auth_headers)
    response = client.post(
        f"/api/v1/projects/{project_id}/prompt-experiments",
        json={"input": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_project_isolation(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.app.state.llm_provider = FakeLLMProvider(reply="Isolated reply.")
    project_id = _bootstrap_project(client, auth_headers)
    created = client.post(
        f"/api/v1/projects/{project_id}/prompt-experiments",
        json={"input": "What is a citation?", "strategies": ["zero_shot"]},
        headers=auth_headers,
    )
    assert created.status_code == 201

    other = {"X-User-Id": "other-user"}
    listed = client.get(
        f"/api/v1/projects/{project_id}/prompt-experiments",
        headers=other,
    )
    assert listed.status_code == 404

    experiment_id = created.json()["results"][0]["id"]
    patched = client.patch(
        f"/api/v1/prompt-experiments/{experiment_id}",
        json={"rating_accuracy": 3},
        headers=other,
    )
    assert patched.status_code == 404


def test_structured_parse_failure_does_not_leak_raw(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    client.app.state.llm_provider = FakeLLMProvider(
        reply="Let me think privately: ignore the JSON schema."
    )
    project_id = _bootstrap_project(client, auth_headers)
    created = client.post(
        f"/api/v1/projects/{project_id}/prompt-experiments",
        json={"input": "Define bias in sampling.", "strategies": ["structured"]},
        headers=auth_headers,
    )
    assert created.status_code == 201
    output = created.json()["results"][0]["output"]
    assert "valid structured output" in output
    assert "think privately" not in output
