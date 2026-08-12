"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

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
    llm_model: str = Field(default="gemini-flash-lite-latest", alias="LLM_MODEL")
    # Prefer GEMINI_API_KEY; LLM_API_KEY is an accepted alias for the same secret.
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")

    llm_timeout_ms: int = Field(default=30_000, alias="LLM_TIMEOUT_MS")
    max_message_chars: int = Field(default=8_000, alias="MAX_MESSAGE_CHARS")
    max_history_messages: int = Field(default=40, alias="MAX_HISTORY_MESSAGES")
    # Demo/dev escape hatch when Gemini quota is exhausted. Never enable in production.
    dev_fake_llm: bool = Field(default=False, alias="DEV_FAKE_LLM")

    embedding_provider: str = Field(default="gemini", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="gemini-embedding-001", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=768, alias="EMBEDDING_DIMENSION")
    embedding_timeout_ms: int = Field(default=60_000, alias="EMBEDDING_TIMEOUT_MS")
    embedding_batch_size: int = Field(default=1, alias="EMBEDDING_BATCH_SIZE")
    embedding_batch_pause_ms: int = Field(default=1_500, alias="EMBEDDING_BATCH_PAUSE_MS")
    # Demo/dev escape hatch when embedding quota is exhausted. Never enable in production.
    dev_fake_embeddings: bool = Field(default=False, alias="DEV_FAKE_EMBEDDINGS")

    storage_provider: str = Field(default="local", alias="STORAGE_PROVIDER")
    storage_local_root: str = Field(
        default=".data/uploads",
        alias="STORAGE_LOCAL_ROOT",
    )
    max_upload_bytes: int = Field(default=20_971_520, alias="MAX_UPLOAD_BYTES")
    max_documents_per_project: int = Field(default=20, alias="MAX_DOCUMENTS_PER_PROJECT")

    chunk_size_chars: int = Field(default=800, alias="CHUNK_SIZE_CHARS")
    chunk_overlap_chars: int = Field(default=150, alias="CHUNK_OVERLAP_CHARS")
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")
    # Cosine distance upper bound (1 - similarity). Lower is more similar / stricter.
    retrieval_max_distance: float = Field(default=0.55, alias="RETRIEVAL_MAX_DISTANCE")
    # Secondary ceiling used when the strict threshold returns nothing.
    retrieval_relaxed_max_distance: float = Field(
        default=0.78,
        alias="RETRIEVAL_RELAXED_MAX_DISTANCE",
    )

    @property
    def resolved_llm_api_key(self) -> str | None:
        return self.gemini_api_key or self.llm_api_key

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def storage_root_path(self) -> Path:
        return Path(self.storage_local_root).expanduser().resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
