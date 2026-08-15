"""Unit tests for search provider helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.errors import ProviderUnavailableError
from app.providers.search import (
    FakeWebSearchProvider,
    FallbackWebSearchProvider,
    WebSearchHit,
    extract_gemini_search_hits,
    parse_duckduckgo_html,
)


def test_extract_gemini_search_hits_from_grounding_chunks() -> None:
    now = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
    response = SimpleNamespace(
        text="Watch dialogue-heavy American films with subtitles to improve English.",
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(
                            web=SimpleNamespace(
                                title="Movies for English learners",
                                uri="https://example.com/english-movies",
                            )
                        ),
                        SimpleNamespace(
                            web={"title": "AFI list", "uri": "https://example.com/afi"}
                        ),
                    ]
                )
            )
        ],
    )
    hits = extract_gemini_search_hits(response, max_results=5, retrieved_at=now)
    assert len(hits) == 2
    assert hits[0].title == "Movies for English learners"
    assert hits[0].url == "https://example.com/english-movies"
    assert hits[0].provider == "gemini-search"
    assert hits[0].snippet is not None
    assert hits[1].url == "https://example.com/afi"
    assert hits[1].snippet is None


def test_extract_gemini_search_hits_empty_without_chunks() -> None:
    now = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
    response = SimpleNamespace(text="No sources.", candidates=[SimpleNamespace()])
    assert extract_gemini_search_hits(response, max_results=5, retrieved_at=now) == []


def test_parse_duckduckgo_html_extracts_ranked_links() -> None:
    now = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
    markup = """
    <div class="result">
      <a rel="nofollow" class="result__a" href="https://example.com/learn-english-movies">
        Best movies to improve English
      </a>
      <a class="result__snippet">American films with subtitles to improve English.</a>
    </div>
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ffluentu.example%2Fmovies">
        10 Classic American Movies
      </a>
      <a class="result__snippet">Classic American movies for English learners.</a>
    </div>
    """
    hits = parse_duckduckgo_html(markup, max_results=5, retrieved_at=now)
    assert [hit.url for hit in hits] == [
        "https://example.com/learn-english-movies",
        "https://fluentu.example/movies",
    ]
    assert hits[0].title == "Best movies to improve English"
    assert hits[0].provider == "duckduckgo-html"
    assert hits[1].snippet is not None


class _BoomSearch(FakeWebSearchProvider):
    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        raise ProviderUnavailableError("Web search is temporarily unavailable. Please try again.")


async def test_fallback_does_not_raise_when_later_provider_returns_empty() -> None:
    provider = FallbackWebSearchProvider(
        _BoomSearch(),
        FakeWebSearchProvider(misses={"q"}),
    )
    assert await provider.search(query="q") == []


async def test_fallback_uses_later_provider_hits() -> None:
    provider = FallbackWebSearchProvider(_BoomSearch(), FakeWebSearchProvider())
    hits = await provider.search(query="python")
    assert hits
    assert hits[0].url.startswith("https://")


async def test_fallback_raises_when_every_provider_fails() -> None:
    provider = FallbackWebSearchProvider(_BoomSearch(), _BoomSearch())
    with pytest.raises(ProviderUnavailableError):
        await provider.search(query="q")
