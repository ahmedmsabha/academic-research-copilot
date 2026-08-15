"""LLM provider protocol and Gemini adapter (google-genai)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from app.core.errors import (
    ProviderConfigError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

ChatRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: list[ChatMessage]
    model: str
    system_instruction: str | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...


def history_to_gemini_contents(messages: list[ChatMessage]) -> list[dict[str, object]]:
    """Map app chat turns to Gemini content dicts (user/model roles)."""
    contents: list[dict[str, object]] = []
    for message in messages:
        if not message.content.strip():
            continue
        role = "user" if message.role == "user" else "model"
        contents.append(
            {
                "role": role,
                "parts": [{"text": message.content}],
            }
        )
    return contents


class GeminiLLMProvider:
    """Google Gemini adapter using the official google-genai SDK."""

    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        default_model: str,
        timeout_ms: int = 30_000,
    ) -> None:
        self._api_key = api_key or ""
        self._default_model = default_model
        self._timeout_ms = timeout_ms
        self._client = None

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

    async def generate(self, request: LLMRequest) -> LLMResponse:
        from google.genai import types

        if not self._api_key:
            raise ProviderConfigError("GEMINI_API_KEY (or LLM_API_KEY) is not set.")

        model = request.model or self._default_model
        contents = history_to_gemini_contents(request.messages)
        if not contents:
            raise ProviderUnavailableError("No valid messages were provided to the model.")

        config: types.GenerateContentConfig | None = None
        if request.system_instruction:
            config = types.GenerateContentConfig(system_instruction=request.system_instruction)

        try:
            client = self._get_client()
            # Prefer async API when available; fall back to sync generate_content.
            if hasattr(client, "aio"):
                response = await client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            else:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
        except ProviderConfigError:
            raise
        except Exception as exc:  # noqa: BLE001 — map provider SDK errors safely
            mapped = _map_provider_exception(exc)
            raise mapped from None

        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise ProviderUnavailableError("The model returned an empty response.")

        prompt_tokens, completion_tokens, total_tokens = _usage_tokens(response)
        return LLMResponse(
            text=text,
            model=model,
            provider=self.provider_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )


def _usage_tokens(response: object) -> tuple[int | None, int | None, int | None]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return None, None, None
    prompt = _optional_int(getattr(usage, "prompt_token_count", None))
    completion = _optional_int(getattr(usage, "candidates_token_count", None))
    total = _optional_int(getattr(usage, "total_token_count", None))
    return prompt, completion, total


def _optional_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _map_provider_exception(
    exc: Exception,
) -> ProviderTimeoutError | ProviderConfigError | ProviderUnavailableError:
    name = type(exc).__name__.lower()
    message = str(exc).lower()

    if "timeout" in name or "timed out" in message or "deadline" in message:
        return ProviderTimeoutError()
    if (
        "api key" in message
        or "authentication" in message
        or "permission" in message
        or "unauthenticated" in message
    ):
        return ProviderConfigError("The AI provider rejected the API credentials.")
    if (
        "404" in message
        or "not_found" in message
        or "no longer available" in message
        or "is not found" in message
    ):
        return ProviderConfigError(
            "The configured LLM model is unavailable. Update LLM_MODEL in your .env "
            "(for example gemini-flash-lite-latest) and restart the AI service."
        )
    if (
        "429" in message
        or "rate limit" in message
        or "rate_limit" in message
        or "resource_exhausted" in message
        or "quota exceeded" in message
        or "exceeded your current quota" in message
    ):
        return ProviderUnavailableError(
            "The AI provider rate limit was reached. Please try again shortly."
        )
    return ProviderUnavailableError()


class FakeLLMProvider:
    """Deterministic provider for tests — never calls an external API."""

    provider_name = "fake"

    def __init__(self, reply: str = "This is a test reply.") -> None:
        self.reply = reply
        self.calls: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        text = self.reply if self.reply else f"Echo: {last_user}"
        return LLMResponse(text=text, model=request.model, provider=self.provider_name)
