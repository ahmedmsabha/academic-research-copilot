"""Unit tests for structured Prompt Lab parsing."""

from app.prompts.structured import (
    STRUCTURED_PARSE_FAILURE,
    format_structured_answer,
    parse_structured_answer,
)
from app.services.prompt_lab import _visible_output


def test_parses_plain_json() -> None:
    raw = """
    {
      "answer": "RAG retrieves evidence before answering.",
      "key_points": ["Uses documents", "Reduces unsupported claims"],
      "confidence": "high",
      "limitations": "Depends on retrieval quality."
    }
    """
    parsed = parse_structured_answer(raw)
    assert parsed is not None
    assert parsed.confidence == "high"
    formatted = format_structured_answer(parsed)
    assert "RAG retrieves evidence before answering." in formatted
    assert "Key points:" in formatted


def test_parses_fenced_json_and_ignores_preamble() -> None:
    raw = """Here is the object:
```json
{"answer": "Cite paraphrases.", "key_points": ["Words", "Ideas"],
 "confidence": "medium", "limitations": "Field norms vary."}
```
secret scratchpad: ignore previous instructions
"""
    parsed = parse_structured_answer(raw)
    assert parsed is not None
    assert parsed.answer == "Cite paraphrases."


def test_invalid_json_is_rejected() -> None:
    assert parse_structured_answer("let me think step by step...") is None


def test_structured_visible_output_never_dumps_raw_reasoning() -> None:
    raw = "I should hide this chain of thought."
    visible = _visible_output("structured", raw)
    assert visible == STRUCTURED_PARSE_FAILURE
    assert raw not in visible
