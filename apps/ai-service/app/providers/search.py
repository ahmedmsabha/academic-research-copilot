"""Web search provider protocol and adapters (Tavily, DuckDuckGo HTML, Instant Answer)."""

from __future__ import annotations

import html as html_lib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.core.errors import ProviderTimeoutError, ProviderUnavailableError

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
_RESULT_LINK = re.compile(
    r'<a\b(?=[^>]*\bclass="[^"]*\bresult__a\b)[^>]*\bhref="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_RESULT_SNIPPET = re.compile(
    r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class WebSearchHit:
    title: str
    url: str
    snippet: str | None
    provider: str
    retrieved_at: datetime


class WebSearchProvider(Protocol):
    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]: ...


class FallbackWebSearchProvider:
    """Try providers in order until one returns hits."""

    provider_name = "web-search"

    def __init__(self, *providers: WebSearchProvider) -> None:
        self._providers = providers

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        last_error: Exception | None = None
        any_success = False
        for provider in self._providers:
            try:
                hits = await provider.search(query=query, max_results=max_results)
            except (ProviderTimeoutError, ProviderUnavailableError) as exc:
                last_error = exc
                logger.warning(
                    "web_search_provider_failed",
                    extra={"provider": getattr(provider, "provider_name", "unknown")},
                )
                continue
            any_success = True
            if hits:
                return hits
        if not any_success and last_error is not None:
            raise last_error
        return []


class WikipediaSearchProvider:
    """MediaWiki search — encyclopedia titles, not a general web search.

    Kept for explicit encyclopedia lookups. Do not use as the default web-search
    fallback: it always returns *some* page, which starves better providers and
    produces irrelevant hits for how-to / recommendation queries.
    """

    provider_name = "wikipedia"
    _url = "https://en.wikipedia.org/w/api.php"

    def __init__(self, *, timeout_ms: int = 12_000) -> None:
        self._timeout = timeout_ms / 1000

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        cleaned = query.strip()
        if not cleaned:
            return []
        now = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self._url,
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": cleaned,
                        "srlimit": max(1, min(max_results, 8)),
                        "srprop": "snippet",
                        "format": "json",
                        "utf8": 1,
                    },
                    headers={"User-Agent": "AcademicResearchCopilot/0.1 (research assistant)"},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Web search timed out. Please try again.") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Web search is temporarily unavailable. Please try again."
            ) from exc

        query_block = payload.get("query") if isinstance(payload, dict) else None
        results = query_block.get("search") if isinstance(query_block, dict) else None
        if not isinstance(results, list):
            return []

        hits: list[WebSearchHit] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            if not title:
                continue
            snippet = _strip_html(str(item.get("snippet") or "").strip()) or None
            wiki_title = title.replace(" ", "_")
            hits.append(
                WebSearchHit(
                    title=title,
                    url=f"https://en.wikipedia.org/wiki/{wiki_title}",
                    snippet=snippet,
                    provider=self.provider_name,
                    retrieved_at=now,
                )
            )
            if len(hits) >= max_results:
                break
        return hits


class DuckDuckGoSearchProvider:
    """DuckDuckGo Instant Answer API — no key required, sparse but safe for demos."""

    provider_name = "duckduckgo"
    _url = "https://api.duckduckgo.com/"

    def __init__(self, *, timeout_ms: int = 12_000) -> None:
        self._timeout = timeout_ms / 1000

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        cleaned = query.strip()
        if not cleaned:
            return []
        now = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    self._url,
                    params={
                        "q": cleaned,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                    headers={"User-Agent": "AcademicResearchCopilot/0.1"},
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Web search timed out. Please try again.") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Web search is temporarily unavailable. Please try again."
            ) from exc

        if not isinstance(payload, dict):
            return []

        hits: list[WebSearchHit] = []
        abstract = str(payload.get("AbstractText") or "").strip()
        abstract_url = str(payload.get("AbstractURL") or "").strip()
        heading = str(payload.get("Heading") or cleaned).strip()
        if abstract and abstract_url:
            hits.append(
                WebSearchHit(
                    title=heading,
                    url=abstract_url,
                    snippet=abstract,
                    provider=self.provider_name,
                    retrieved_at=now,
                )
            )

        for group_name in ("Results", "RelatedTopics"):
            items = payload.get(group_name) or []
            if not isinstance(items, list):
                continue
            for item in items:
                hit = _topic_to_hit(item, provider=self.provider_name, retrieved_at=now)
                if hit is not None:
                    hits.append(hit)
                if len(hits) >= max_results:
                    return _dedupe(hits, max_results)

        return _dedupe(hits, max_results)


class DuckDuckGoHtmlSearchProvider:
    """DuckDuckGo HTML results — real ranked links, no API key."""

    provider_name = "duckduckgo-html"
    _url = "https://html.duckduckgo.com/html/"

    def __init__(self, *, timeout_ms: int = 12_000) -> None:
        self._timeout = timeout_ms / 1000

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        cleaned = query.strip()
        if not cleaned:
            return []
        now = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": _BROWSER_UA},
            ) as client:
                response = await client.post(
                    self._url,
                    data={"q": cleaned},
                )
                if response.status_code in {202, 403, 429}:
                    raise ProviderUnavailableError(
                        "Web search is temporarily unavailable. Please try again."
                    )
                response.raise_for_status()
                payload = response.text
        except ProviderUnavailableError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Web search timed out. Please try again.") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Web search is temporarily unavailable. Please try again."
            ) from exc

        return parse_duckduckgo_html(payload, max_results=max_results, retrieved_at=now)


class TavilySearchProvider:
    """Tavily search when WEB_SEARCH_API_KEY is configured."""

    provider_name = "tavily"
    _url = "https://api.tavily.com/search"

    def __init__(self, *, api_key: str, timeout_ms: int = 12_000) -> None:
        self._api_key = api_key
        self._timeout = timeout_ms / 1000

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        cleaned = query.strip()
        if not cleaned:
            return []
        now = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._url,
                    json={
                        "api_key": self._api_key,
                        "query": cleaned,
                        "max_results": max_results,
                        "include_answer": False,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Web search timed out. Please try again.") from exc
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailableError(
                "Web search is temporarily unavailable. Please try again."
            ) from exc

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return []

        hits: list[WebSearchHit] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or url).strip()
            snippet = str(item.get("content") or item.get("snippet") or "").strip() or None
            if not url:
                continue
            hits.append(
                WebSearchHit(
                    title=title or url,
                    url=url,
                    snippet=snippet,
                    provider=self.provider_name,
                    retrieved_at=now,
                )
            )
            if len(hits) >= max_results:
                break
        return hits


class GeminiSearchProvider:
    """Google Search grounding via Gemini — real ranked web sources, uses GEMINI_API_KEY."""

    provider_name = "gemini-search"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_ms: int = 30_000,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_ms = timeout_ms
        self._client = None

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
        return self._client

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        cleaned = query.strip()
        if not cleaned:
            return []
        from google.genai import types

        prompt = (
            "Use Google Search to find web pages that answer this query. "
            "Prefer practical guides, ranked lists, and recent articles over "
            "encyclopedia overviews when the query asks for recommendations or methods.\n"
            f"Query: {cleaned}"
        )
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
        now = datetime.now(UTC)
        try:
            client = self._get_client()
            if hasattr(client, "aio"):
                response = await client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                )
            else:
                response = client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=config,
                )
        except Exception as exc:  # noqa: BLE001 — map SDK errors without leaking internals
            logger.warning("gemini_search_failed", extra={"error_type": type(exc).__name__})
            raise _map_search_exception(exc) from exc

        return extract_gemini_search_hits(response, max_results=max_results, retrieved_at=now)


class FakeWebSearchProvider:
    """Deterministic search provider for tests — never calls the network."""

    provider_name = "fake-search"

    def __init__(
        self,
        hits: list[WebSearchHit] | None = None,
        misses: set[str] | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.misses = {item.lower() for item in (misses or set())}
        now = datetime(2026, 8, 14, 10, 0, tzinfo=UTC)
        self.hits = hits or [
            WebSearchHit(
                title="Python 3.13 release notes",
                url="https://example.com/python-3-13",
                snippet="Python 3.13 includes performance improvements and typing updates.",
                provider=self.provider_name,
                retrieved_at=now,
            ),
            WebSearchHit(
                title="What's new in Python",
                url="https://example.com/whats-new-python",
                snippet="A summary of recent CPython releases for application developers.",
                provider=self.provider_name,
                retrieved_at=now,
            ),
        ]

    async def search(self, *, query: str, max_results: int = 5) -> list[WebSearchHit]:
        self.calls.append(query)
        if not query.strip() or query.strip().lower() in self.misses:
            return []
        return self.hits[:max_results]


def parse_duckduckgo_html(
    markup: str,
    *,
    max_results: int,
    retrieved_at: datetime,
) -> list[WebSearchHit]:
    """Parse DuckDuckGo HTML SERP markup into WebSearchHit values."""
    links = _RESULT_LINK.findall(markup)
    snippets = [_strip_html(snippet) for snippet in _RESULT_SNIPPET.findall(markup)]
    hits: list[WebSearchHit] = []
    for index, (href, title_html) in enumerate(links):
        url = _normalize_result_url(href)
        if url is None:
            continue
        title = _strip_html(title_html) or url
        snippet = snippets[index] if index < len(snippets) else None
        hits.append(
            WebSearchHit(
                title=title,
                url=url,
                snippet=snippet or None,
                provider=DuckDuckGoHtmlSearchProvider.provider_name,
                retrieved_at=retrieved_at,
            )
        )
        if len(hits) >= max_results:
            break
    return _dedupe(hits, max_results)


def _normalize_result_url(href: str) -> str | None:
    url = html_lib.unescape(href).strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if "uddg=" in (parsed.query or ""):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            url = unquote(target)
            parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    host = (parsed.netloc or "").lower()
    if "duckduckgo.com" in host:
        return None
    return url


def extract_gemini_search_hits(
    response: object,
    *,
    max_results: int,
    retrieved_at: datetime,
) -> list[WebSearchHit]:
    """Turn Gemini grounding_chunks into WebSearchHit values (no SDK required in tests)."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) if metadata is not None else None
    if not chunks:
        return []
    generated = (getattr(response, "text", None) or "").strip()
    hits: list[WebSearchHit] = []
    for index, chunk in enumerate(chunks):
        web = _web_from_chunk(chunk)
        if web is None:
            continue
        uri, title = web
        snippet = generated[:400] if index == 0 and generated else None
        hits.append(
            WebSearchHit(
                title=title or uri,
                url=uri,
                snippet=snippet,
                provider=GeminiSearchProvider.provider_name,
                retrieved_at=retrieved_at,
            )
        )
        if len(hits) >= max_results:
            break
    return hits


def _web_from_chunk(chunk: object) -> tuple[str, str] | None:
    web = getattr(chunk, "web", None)
    if web is None and isinstance(chunk, dict):
        web = chunk.get("web")
    if web is None:
        return None
    if isinstance(web, dict):
        uri = str(web.get("uri") or "").strip()
        title = str(web.get("title") or uri).strip()
    else:
        uri = str(getattr(web, "uri", None) or "").strip()
        title = str(getattr(web, "title", None) or uri).strip()
    if not uri:
        return None
    return uri, title or uri


def _map_search_exception(exc: Exception) -> ProviderTimeoutError | ProviderUnavailableError:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timed out" in message or "deadline" in message:
        return ProviderTimeoutError("Web search timed out. Please try again.")
    return ProviderUnavailableError("Web search is temporarily unavailable. Please try again.")


def _topic_to_hit(
    item: object,
    *,
    provider: str,
    retrieved_at: datetime,
) -> WebSearchHit | None:
    if not isinstance(item, dict):
        return None
    url = str(item.get("FirstURL") or item.get("url") or "").strip()
    text = str(item.get("Text") or item.get("title") or "").strip()
    if not url:
        topics = item.get("Topics")
        if isinstance(topics, list) and topics:
            return _topic_to_hit(topics[0], provider=provider, retrieved_at=retrieved_at)
        return None
    title = text.split(" - ", maxsplit=1)[0].strip() or url
    snippet = text or None
    return WebSearchHit(
        title=title,
        url=url,
        snippet=snippet,
        provider=provider,
        retrieved_at=retrieved_at,
    )


def _strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    unescaped = (
        without_tags.replace("&quot;", '"')
        .replace("&#039;", "'")
        .replace("&amp;", "&")
        .replace("&nbsp;", " ")
    )
    return re.sub(r"\s+", " ", unescaped).strip()


def _dedupe(hits: list[WebSearchHit], max_results: int) -> list[WebSearchHit]:
    seen: set[str] = set()
    unique: list[WebSearchHit] = []
    for hit in hits:
        key = hit.url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
        if len(unique) >= max_results:
            break
    return unique
