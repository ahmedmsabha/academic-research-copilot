"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration for the AI service."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-2.0-flash", alias="LLM_MODEL")
    # Prefer GEMINI_API_KEY; LLM_API_KEY is an accepted alias for the same secret.
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")

    llm_timeout_ms: int = Field(default=30_000, alias="LLM_TIMEOUT_MS")
    max_message_chars: int = Field(default=8_000, alias="MAX_MESSAGE_CHARS")
    max_history_messages: int = Field(default=40, alias="MAX_HISTORY_MESSAGES")
    # Demo/dev escape hatch when Gemini quota is exhausted. Never enable in production.
    dev_fake_llm: bool = Field(default=False, alias="DEV_FAKE_LLM")

    @property
    def resolved_llm_api_key(self) -> str | None:
        return self.gemini_api_key or self.llm_api_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
