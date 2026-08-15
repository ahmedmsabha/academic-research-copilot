"""Safe arithmetic calculator. Never uses eval, exec, or shell execution."""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.tools.errors import ToolError

Number = int | float

_MAX_ABS_VALUE = 1e15
_MAX_POW_EXPONENT = 12
_MAX_NODES = 64

_BIN_OPS: dict[type[ast.operator], Callable[[Number, Number], Number]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.unaryop], Callable[[Number], Number]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_WORD_OPERATORS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmultiplied by\b", re.IGNORECASE), "*"),
    (re.compile(r"\bdivided by\b", re.IGNORECASE), "/"),
    (re.compile(r"\bplus\b", re.IGNORECASE), "+"),
    (re.compile(r"\bminus\b", re.IGNORECASE), "-"),
    (re.compile(r"\btimes\b", re.IGNORECASE), "*"),
)

_LEADING_PHRASE = re.compile(
    r"^\s*(?:please\s+)?(?:what(?:'s| is)|calculate|compute|evaluate|solve)\s+",
    re.IGNORECASE,
)
_HAS_OPERATOR = re.compile(r"[+\-*/%]")
_ALLOWED_EXPR = re.compile(r"^[\d\s+\-*/().%*]+$")


@dataclass(frozen=True, slots=True)
class CalculatorResult:
    expression: str
    normalized_expression: str
    value: Number


def extract_expression(text: str) -> str | None:
    """Return a candidate arithmetic expression, or None if the text is not numeric."""
    cleaned = text.strip().rstrip("?.!")
    cleaned = _LEADING_PHRASE.sub("", cleaned, count=1).strip()
    for pattern, replacement in _WORD_OPERATORS:
        cleaned = pattern.sub(replacement, cleaned)
    normalized = cleaned.replace("^", "**")
    compact = re.sub(r"\s+", "", normalized)
    if not compact or not _HAS_OPERATOR.search(compact):
        return None
    if not _ALLOWED_EXPR.match(normalized):
        return None
    if compact.lstrip("+-").replace(".", "", 1).isdigit():
        return None
    return normalized


def evaluate_expression(expression: str, *, max_chars: int = 200) -> CalculatorResult:
    """Evaluate a numeric expression with a restricted AST."""
    raw = expression.strip()
    if not raw:
        raise ToolError("Provide a numeric expression to calculate.", code="EMPTY_EXPRESSION")
    if len(raw) > max_chars:
        raise ToolError(
            f"Expression exceeds the maximum length of {max_chars} characters.",
            code="EXPRESSION_TOO_LONG",
        )

    normalized = _normalize(raw)
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise ToolError(
            "I couldn't parse that as a numeric expression.",
            code="INVALID_SYNTAX",
        ) from exc

    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > _MAX_NODES:
        raise ToolError("Expression is too complex.", code="EXPRESSION_TOO_COMPLEX")

    try:
        value = _eval_node(tree.body)
    except ToolError:
        raise
    except ZeroDivisionError as exc:
        raise ToolError("Division by zero is not allowed.", code="DIVISION_BY_ZERO") from exc
    except OverflowError as exc:
        raise ToolError("The result is too large to compute safely.", code="OVERFLOW") from exc

    if isinstance(value, float) and (value != value or abs(value) == float("inf")):  # noqa: PLR0124
        raise ToolError("The result is not a finite number.", code="NON_FINITE")
    if abs(float(value)) > _MAX_ABS_VALUE:
        raise ToolError("The result is too large to compute safely.", code="OVERFLOW")

    display_value: Number
    if isinstance(value, float) and value.is_integer():
        display_value = int(value)
    else:
        display_value = value
    return CalculatorResult(
        expression=raw,
        normalized_expression=normalized,
        value=display_value,
    )


def _normalize(expression: str) -> str:
    cleaned = expression.strip()
    for pattern, replacement in _WORD_OPERATORS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned.replace("^", "**")


def _eval_node(node: ast.AST) -> Number:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError("Only numeric values are allowed.", code="INVALID_SYNTAX")
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(float(right)) > _MAX_POW_EXPONENT:
            raise ToolError("Exponent is too large.", code="OVERFLOW")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and float(right) == 0.0:
            raise ToolError("Division by zero is not allowed.", code="DIVISION_BY_ZERO")
        return _BIN_OPS[type(node.op)](left, right)
    raise ToolError("I couldn't parse that as a numeric expression.", code="INVALID_SYNTAX")
