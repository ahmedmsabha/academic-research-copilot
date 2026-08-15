"""Parse structured Prompt Lab output. Never treat leftover model text as the result."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

Confidence = Literal["high", "medium", "low"]

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


class StructuredLabAnswer(BaseModel):
    answer: str = Field(..., min_length=1, max_length=4000)
    key_points: list[str] = Field(..., min_length=1, max_length=8)
    confidence: Confidence
    limitations: str = Field(..., min_length=1, max_length=2000)

    @field_validator("answer", "limitations")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank.")
        return cleaned

    @field_validator("key_points")
    @classmethod
    def strip_points(cls, value: list[str]) -> list[str]:
        points = [item.strip() for item in value if item.strip()]
        if not points:
            raise ValueError("key_points cannot be empty.")
        return points[:8]


def extract_json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if not text:
        return None
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        parsed: Any = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_structured_answer(raw: str) -> StructuredLabAnswer | None:
    payload = extract_json_object(raw)
    if payload is None:
        return None
    try:
        return StructuredLabAnswer.model_validate(payload)
    except ValidationError:
        return None


def format_structured_answer(parsed: StructuredLabAnswer) -> str:
    points = "\n".join(f"- {item}" for item in parsed.key_points)
    return (
        f"{parsed.answer}\n\n"
        f"Key points:\n{points}\n\n"
        f"Confidence: {parsed.confidence}\n"
        f"Limitations: {parsed.limitations}"
    )


STRUCTURED_PARSE_FAILURE = (
    "The model did not return valid structured output for this run. "
    "No hidden reasoning is shown. Try the comparison again."
)
