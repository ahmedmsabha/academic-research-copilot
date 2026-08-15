"""Unit tests for the safe calculator tool."""

from __future__ import annotations

import pytest

from app.tools.calculator import evaluate_expression, extract_expression
from app.tools.errors import ToolError


def test_precedence_and_parentheses() -> None:
    result = evaluate_expression("12 * (3 + 4)")
    assert result.value == 84
    assert result.normalized_expression == "12 * (3 + 4)"


def test_decimals_and_unary_minus() -> None:
    result = evaluate_expression("-2.5 + 1.5")
    assert result.value == -1.0


def test_word_operators() -> None:
    result = evaluate_expression("12 times 4")
    assert result.value == 48


def test_power_caret() -> None:
    result = evaluate_expression("2^3")
    assert result.value == 8


def test_division_by_zero() -> None:
    with pytest.raises(ToolError) as exc:
        evaluate_expression("10 / 0")
    assert exc.value.code == "DIVISION_BY_ZERO"


def test_invalid_syntax_rejects_names() -> None:
    with pytest.raises(ToolError) as exc:
        evaluate_expression("__import__('os')")
    assert exc.value.code == "INVALID_SYNTAX"


def test_oversized_expression() -> None:
    with pytest.raises(ToolError) as exc:
        evaluate_expression("1+" * 120 + "1", max_chars=50)
    assert exc.value.code == "EXPRESSION_TOO_LONG"


def test_extract_expression_from_question() -> None:
    assert extract_expression("What is 12 * (3 + 4)?") == "12 * (3 + 4)"
    assert extract_expression("calculate 2 plus 2") == "2 + 2"
    assert extract_expression("Explain embeddings briefly.") is None
