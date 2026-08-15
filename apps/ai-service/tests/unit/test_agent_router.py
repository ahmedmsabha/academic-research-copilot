"""Unit tests for constrained agent route selection."""

from __future__ import annotations

from app.agent.router import select_route
from app.providers.llm import FakeLLMProvider


async def test_deterministic_calculator() -> None:
    decision = await select_route(
        text="What is 12 * (3 + 4)?",
        preferred="auto",
        has_ready_documents=True,
        llm=FakeLLMProvider(reply="should not be used"),
        model="fake",
    )
    assert decision.route == "calculator"
    assert decision.source == "deterministic"


async def test_deterministic_weather() -> None:
    decision = await select_route(
        text="What's the weather in Paris?",
        preferred="auto",
        has_ready_documents=False,
        llm=FakeLLMProvider(reply="should not be used"),
        model="fake",
    )
    assert decision.route == "weather"


async def test_deterministic_web_search() -> None:
    decision = await select_route(
        text="Search the web for the latest Python release",
        preferred="auto",
        has_ready_documents=False,
        llm=FakeLLMProvider(reply="should not be used"),
        model="fake",
    )
    assert decision.route == "web_search"
    assert decision.tool_input == "the latest Python release"


async def test_document_hint_beats_weather_keyword() -> None:
    decision = await select_route(
        text="What weather events does this paper describe?",
        preferred="auto",
        has_ready_documents=True,
        llm=FakeLLMProvider(reply="should not be used"),
        model="fake",
    )
    assert decision.route == "rag"


async def test_pinned_llm_mode_skips_tools() -> None:
    decision = await select_route(
        text="What is 2+2?",
        preferred="llm",
        has_ready_documents=False,
        llm=FakeLLMProvider(reply="should not be used"),
        model="fake",
    )
    assert decision.route == "llm"
    assert decision.source == "preferred"


async def test_llm_json_route_is_used() -> None:
    llm = FakeLLMProvider(reply='{"route":"web_search","tool_input":"python 3.13"}')
    decision = await select_route(
        text="What changed in the newest CPython?",
        preferred="auto",
        has_ready_documents=False,
        llm=llm,
        model="fake",
    )
    assert decision.route == "web_search"
    assert decision.tool_input == "python 3.13"
    assert decision.source == "llm"


async def test_invalid_llm_json_falls_back_to_llm() -> None:
    decision = await select_route(
        text="Explain embeddings briefly.",
        preferred="auto",
        has_ready_documents=False,
        llm=FakeLLMProvider(reply="Hello from the fake model."),
        model="fake",
    )
    assert decision.route == "llm"
    assert decision.source == "fallback"


async def test_invalid_llm_json_falls_back_to_rag_when_docs_ready() -> None:
    decision = await select_route(
        text="What do neural embeddings map text to?",
        preferred="auto",
        has_ready_documents=True,
        llm=FakeLLMProvider(reply="Hello from the fake model."),
        model="fake",
    )
    assert decision.route == "rag"
    assert decision.source == "fallback"
