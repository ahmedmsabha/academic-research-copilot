"""Unit tests for Gemini history mapping."""

from app.providers.llm import ChatMessage, history_to_gemini_contents


def test_history_to_gemini_contents_maps_roles() -> None:
    contents = history_to_gemini_contents(
        [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
            ChatMessage(role="user", content="What is RAG?"),
        ]
    )
    assert contents == [
        {"role": "user", "parts": [{"text": "Hello"}]},
        {"role": "model", "parts": [{"text": "Hi there"}]},
        {"role": "user", "parts": [{"text": "What is RAG?"}]},
    ]


def test_history_to_gemini_contents_skips_blank() -> None:
    contents = history_to_gemini_contents(
        [
            ChatMessage(role="user", content="  "),
            ChatMessage(role="user", content="Keep me"),
        ]
    )
    assert contents == [{"role": "user", "parts": [{"text": "Keep me"}]}]
