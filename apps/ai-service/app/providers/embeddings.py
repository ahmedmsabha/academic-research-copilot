"""Embedding provider protocol and adapters."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import random
import re
from dataclasses import dataclass
from typing import Protocol

from app.core.errors import (
    ProviderConfigError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)

# Keep batches tiny: Gemini free/dev quotas are easy to exhaust during PDF indexing.
DEFAULT_EMBED_BATCH_SIZE = 1
DEFAULT_EMBED_BATCH_PAUSE_MS = 1_500
DEFAULT_EMBED_MAX_RETRIES = 8


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    vectors: list[list[float]]
    model: str
    provider: str
    dimension: int


class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> EmbeddingResponse: ...


class GeminiEmbeddingProvider:
    """Google Gemini embedding adapter using google-genai."""

    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        dimension: int = 768,
        timeout_ms: int = 60_000,
        batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
        batch_pause_ms: int = DEFAULT_EMBED_BATCH_PAUSE_MS,
        max_retries: int = DEFAULT_EMBED_MAX_RETRIES,
    ) -> None:
        self._api_key = api_key or ""
        self._model = model
        self._dimension = dimension
        self._timeout_ms = timeout_ms
        self._batch_size = max(1, batch_size)
        self._batch_pause_ms = max(0, batch_pause_ms)
        self._max_retries = max(1, max_retries)
        self._client = None
        # Serialize outbound embed calls so concurrent document jobs don't stampede the quota.
        self._request_lock = asyncio.Lock()

    def _get_client(self):  # type: ignore[no-untyped-def]
        if not self._api_key:
            raise ProviderConfigError("GEMINI_API_KEY (or LLM_API_KEY) is not set.")
        if self._client is None:
            from google import genai
            from google.genai import types

            self._client = genai.Client(
                api_key=self._api_key,
                http_options=types.HttpOptions(timeout=self._timeout_ms),
            )
        return self._client

    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        if not self._api_key:
            raise ProviderConfigError("GEMINI_API_KEY (or LLM_API_KEY) is not set.")
        cleaned = [text.strip() for text in texts if text and text.strip()]
        if not cleaned:
            return EmbeddingResponse(
                vectors=[],
                model=self._model,
                provider=self.provider_name,
                dimension=self._dimension,
            )

        vectors: list[list[float]] = []
        batch_starts = list(range(0, len(cleaned), self._batch_size))
        for index, start in enumerate(batch_starts):
            if index > 0 and self._batch_pause_ms:
                await asyncio.sleep(self._batch_pause_ms / 1000)
            batch = cleaned[start : start + self._batch_size]
            vectors.extend(await self._embed_batch(batch))

        if len(vectors) != len(cleaned):
            raise ProviderUnavailableError("The embedding provider returned an unexpected result.")

        return EmbeddingResponse(
            vectors=vectors,
            model=self._model,
            provider=self.provider_name,
            dimension=self._dimension,
        )

    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return await self._embed_batch_once(batch)
            except Exception as exc:  # noqa: BLE001
                mapped = (
                    exc
                    if isinstance(
                        exc,
                        (ProviderConfigError, ProviderTimeoutError, ProviderUnavailableError),
                    )
                    else _map_embedding_exception(exc)
                )
                last_error = mapped

                # Large batches often trip free-tier limits; fall back to one text at a time.
                if (
                    _is_rate_limit_error(mapped)
                    and len(batch) > 1
                    and attempt == 0
                ):
                    logger.warning(
                        "embedding_batch_falling_back_to_singles",
                        extra={"batch_size": len(batch)},
                    )
                    vectors: list[list[float]] = []
                    for index, text in enumerate(batch):
                        if index > 0 and self._batch_pause_ms:
                            await asyncio.sleep(self._batch_pause_ms / 1000)
                        vectors.extend(await self._embed_batch([text]))
                    return vectors

                if not _is_rate_limit_error(mapped) or attempt >= self._max_retries - 1:
                    raise mapped from None

                delay = _retry_delay_seconds(attempt, mapped)
                logger.warning(
                    "embedding_rate_limited_retrying",
                    extra={
                        "attempt": attempt + 1,
                        "delay_s": round(delay, 2),
                        "batch_size": len(batch),
                    },
                )
                await asyncio.sleep(delay)
        assert last_error is not None
        raise last_error

    async def _embed_batch_once(self, batch: list[str]) -> list[list[float]]:
        try:
            async with self._request_lock:
                client = self._get_client()
                if hasattr(client, "aio"):
                    response = await client.aio.models.embed_content(
                        model=self._model,
                        contents=batch,
                        config={"output_dimensionality": self._dimension},
                    )
                else:
                    response = client.models.embed_content(
                        model=self._model,
                        contents=batch,
                        config={"output_dimensionality": self._dimension},
                    )
        except ProviderConfigError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "embedding_batch_failed",
                extra={
                    "batch_size": len(batch),
                    "error_type": type(exc).__name__,
                    "status_code": getattr(exc, "status_code", None)
                    or getattr(getattr(exc, "response", None), "status_code", None),
                },
            )
            raise _map_embedding_exception(exc) from None

        embeddings = getattr(response, "embeddings", None) or []
        vectors: list[list[float]] = []
        for item in embeddings:
            values = getattr(item, "values", None)
            if values is None and isinstance(item, dict):
                values = item.get("values")
            if not values:
                raise ProviderUnavailableError("The embedding provider returned an empty vector.")
            vectors.append([float(v) for v in values])

        if len(vectors) != len(batch):
            raise ProviderUnavailableError("The embedding provider returned an unexpected result.")
        return vectors


class FakeEmbeddingProvider:
    """Deterministic bag-of-tokens embeddings for tests — never calls an external API."""

    provider_name = "fake"

    def __init__(self, *, dimension: int = 768) -> None:
        self._dimension = dimension
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> EmbeddingResponse:
        cleaned = [text.strip() for text in texts if text and text.strip()]
        self.calls.append(cleaned)
        vectors = [_hash_embedding(text, self._dimension) for text in cleaned]
        return EmbeddingResponse(
            vectors=vectors,
            model="fake-embedding",
            provider=self.provider_name,
            dimension=self._dimension,
        )


def _hash_embedding(text: str, dimension: int) -> list[float]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    vector = [0.0] * dimension
    if not tokens:
        vector[0] = 1.0
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "rate limit" in message
        or "try again shortly" in message
        or "wait a minute" in message
        or "resource_exhausted" in message
        or "quota exceeded" in message
        or "exceeded your current quota" in message
        or "429" in message
    )


def _retry_delay_seconds(attempt: int, exc: Exception) -> float:
    """Exponential backoff with jitter; honor Retry-After when present."""
    retry_after = _extract_retry_after_seconds(exc)
    if retry_after is not None:
        return min(90.0, max(1.0, retry_after) + random.uniform(0.1, 0.8))
    # Free-tier quotas often need tens of seconds between bursts.
    base = min(60.0, 2.0 * (2**attempt))
    return base + random.uniform(0.2, 1.2)


def _extract_retry_after_seconds(exc: Exception) -> float | None:
    for attr in ("retry_after", "retry_delay"):
        value = getattr(exc, attr, None)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    message = str(exc)
    match = re.search(r"retry[- ]after[:\s]*([0-9]+(?:\.[0-9]+)?)", message, re.IGNORECASE)
    if match:
        return float(match.group(1))
    # Google sometimes embeds "Please retry in 32.4s".
    match = re.search(r"retry in ([0-9]+(?:\.[0-9]+)?)s", message, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _map_embedding_exception(
    exc: Exception,
) -> ProviderTimeoutError | ProviderConfigError | ProviderUnavailableError:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    status_code = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )

    if "timeout" in name or "timed out" in message or "deadline" in message:
        return ProviderTimeoutError("The embedding provider timed out. Please try again.")
    if (
        "api key" in message
        or "authentication" in message
        or "permission" in message
        or "unauthenticated" in message
    ):
        return ProviderConfigError("The embedding provider rejected the API credentials.")
    if (
        "404" in message
        or "not_found" in message
        or "is not found" in message
        or "not supported for embedcontent" in message
    ):
        return ProviderConfigError(
            "The configured embedding model is unavailable. Update EMBEDDING_MODEL in your .env "
            "(for example gemini-embedding-001) and restart the AI service."
        )
    if (
        status_code == 429
        or "429" in message
        or "rate limit" in message
        or "rate_limit" in message
        or "resource_exhausted" in message
        or "quota exceeded" in message
        or "exceeded your current quota" in message
    ):
        return ProviderUnavailableError(
            "The embedding provider rate limit was reached. "
            "Please wait a minute, then retry indexing."
        )
    if "payload" in message or "too large" in message or "invalid_argument" in message:
        return ProviderUnavailableError(
            "The document produced too much text for one embedding request. "
            "Try a shorter PDF, or retry after the service batches embeddings."
        )
    return ProviderUnavailableError(
        "The embedding provider could not index this document. Please retry shortly."
    )
