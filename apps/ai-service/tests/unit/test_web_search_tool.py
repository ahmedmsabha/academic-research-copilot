"""Unit tests for web-search query retries and relevance filtering."""

from __future__ import annotations

from datetime import UTC, datetime

from app.providers.search import FakeWebSearchProvider, WebSearchHit
from app.tools.web_search import run_web_search, search_query_variants, select_relevant_hits

_NOW = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)


def test_search_variants_keep_purpose() -> None:
    variants = search_query_variants("Search the web for American movies to improve English")
    assert variants[0] == "American movies to improve English"
    assert all("english" in variant.lower() for variant in variants)
    assert "American movies" not in variants
    assert any(variant.lower().startswith("best ") for variant in variants)


async def test_search_retries_until_a_variant_hits() -> None:
    provider = FakeWebSearchProvider(
        misses={"american movies to improve english"},
        hits=[
            WebSearchHit(
                title="Best American movies to learn English",
                url="https://example.com/learn-english-movies",
                snippet="Watch American films with subtitles to improve English listening.",
                provider="fake-search",
                retrieved_at=_NOW,
            )
        ],
    )
    hits = await run_web_search(
        provider=provider,
        text="Search the web for American movies to improve English",
    )
    assert hits
    assert len(provider.calls) >= 2
    assert provider.calls[0] == "American movies to improve English"
    assert any(call.lower().startswith("best ") for call in provider.calls)


def test_select_relevant_hits_drops_encyclopedia_pages() -> None:
    hits = [
        WebSearchHit(
            title="Cinema of the United States",
            url="https://en.wikipedia.org/wiki/Cinema_of_the_United_States",
            snippet="The cinema of the United States, consisting mainly of major film studios.",
            provider="wikipedia",
            retrieved_at=_NOW,
        ),
        WebSearchHit(
            title="American Hustle",
            url="https://en.wikipedia.org/wiki/American_Hustle",
            snippet="A 2013 American crime film.",
            provider="wikipedia",
            retrieved_at=_NOW,
        ),
        WebSearchHit(
            title="Best movies to improve English",
            url="https://example.com/learn-english-movies",
            snippet="American movies with clear dialogue to improve English.",
            provider="gemini-search",
            retrieved_at=_NOW,
        ),
    ]
    kept = select_relevant_hits("American movies to improve English", hits)
    assert [hit.title for hit in kept] == ["Best movies to improve English"]
