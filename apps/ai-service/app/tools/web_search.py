"""Web search tool: sanitize the query, retry intent-preserving variants, then call a provider."""

from __future__ import annotations

import re

from app.models.schemas import WebSourceResponse
from app.providers.search import WebSearchHit, WebSearchProvider
from app.tools.errors import ToolError

_SEARCH_PREFIX = re.compile(
    r"^\s*(?:please\s+)?(?:"
    r"search(?:\s+the\s+web)?(?:\s+for)?|"
    r"look(?:\s+it)?\s+up(?:\s+online)?(?:\s+for)?|"
    r"google|"
    r"find(?:\s+online)?"
    r")\s+",
    re.IGNORECASE,
)
_PURPOSE_CLAUSE = re.compile(
    r"\s+(?:to|for|that|which|so that)\s+.+$",
    re.IGNORECASE,
)
_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "of",
    "in",
    "on",
    "for",
    "to",
    "with",
    "about",
    "please",
    "some",
    "any",
    "best",
    "how",
}


def extract_search_query(text: str) -> str:
    cleaned = text.strip()
    cleaned = _SEARCH_PREFIX.sub("", cleaned).strip().rstrip("?.!")
    return cleaned[:300]


def search_query_variants(text: str, query_override: str | None = None) -> list[str]:
    """Keep the full information need. Retry with expansions, never by dropping purpose."""
    primary = (query_override or extract_search_query(text)).strip()
    variants: list[str] = []
    _add_unique(variants, primary)
    if not primary:
        return variants
    lowered = primary.lower()
    if not lowered.startswith(("best ", "how to ", "how do ")):
        _add_unique(variants, f"best {primary}")
    for_form = re.sub(r"\bto\b", "for", primary, count=1, flags=re.I)
    _add_unique(variants, for_form)
    return variants


def select_relevant_hits(query: str, hits: list[WebSearchHit]) -> list[WebSearchHit]:
    """Drop hits that ignore the user's purpose (e.g. encyclopedia pages for a how-to query)."""
    query_tokens = _content_tokens(query)
    purpose = _purpose_tokens(query)
    if not query_tokens:
        return list(hits)
    selected: list[WebSearchHit] = []
    for hit in hits:
        blob_tokens = _content_tokens(f"{hit.title} {hit.snippet or ''}")
        if purpose and purpose.isdisjoint(blob_tokens):
            continue
        overlap = len(query_tokens & blob_tokens) / len(query_tokens)
        if overlap < 0.2:
            continue
        selected.append(hit)
    return selected


async def run_web_search(
    *,
    provider: WebSearchProvider,
    text: str,
    query_override: str | None = None,
    max_results: int = 5,
) -> list[WebSearchHit]:
    variants = search_query_variants(text, query_override)
    if not variants:
        raise ToolError(
            "I can search the web, but I need a topic. Try “search the web for RAG citations”.",
            code="QUERY_REQUIRED",
        )
    primary = variants[0]
    for query in variants:
        hits = await provider.search(query=query, max_results=max_results)
        relevant = select_relevant_hits(primary, hits)
        if relevant:
            return relevant
    return []


def format_web_search_fallback(hits: list[WebSearchHit]) -> str:
    if not hits:
        return (
            "This answer would use web search, which is external information — not your uploaded "
            "documents. I didn't find usable results for that query. Try a more specific topic."
        )
    lines = [
        "This answer uses an external web search tool, not your uploaded documents. "
        "It is not exhaustive research.",
        "",
    ]
    for index, hit in enumerate(hits, start=1):
        snippet = f" — {hit.snippet}" if hit.snippet else ""
        lines.append(f"{index}. [{hit.title}]({hit.url}){snippet}")
    return "\n".join(lines)


def web_hits_to_sources(hits: list[WebSearchHit]) -> list[WebSourceResponse]:
    return [
        WebSourceResponse(
            title=hit.title,
            url=hit.url,
            snippet=hit.snippet,
            provider=hit.provider,
            retrieved_at=hit.retrieved_at,
        )
        for hit in hits
    ]


def _purpose_tokens(query: str) -> set[str]:
    match = _PURPOSE_CLAUSE.search(query)
    if not match:
        return set()
    return _content_tokens(match.group(0))


def _content_tokens(text: str) -> set[str]:
    return {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9']+", text)
        if word.lower() not in _STOPWORDS and len(word) > 1
    }


def _add_unique(items: list[str], value: str) -> None:
    cleaned = re.sub(r"\s+", " ", value).strip()[:300]
    if not cleaned:
        return
    lowered = cleaned.lower()
    if any(existing.lower() == lowered for existing in items):
        return
    items.append(cleaned)
