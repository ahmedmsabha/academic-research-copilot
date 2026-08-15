"""Derive a short conversation title from the first user message."""

from __future__ import annotations

DEFAULT_CONVERSATION_TITLES = frozenset(
    {
        "New chat",
        "Research chat",
        "General chat",
        "Document chat",
        "Agent chat",
    }
)


def title_from_message(content: str, *, max_len: int = 72) -> str:
    compact = " ".join(content.split())
    if not compact:
        return "New chat"
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1].rstrip() + "…"


def should_retitle(current_title: str) -> bool:
    return current_title.strip() in DEFAULT_CONVERSATION_TITLES
