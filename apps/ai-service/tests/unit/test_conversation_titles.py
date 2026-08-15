from app.core.config import Settings
from app.services.conversation_titles import should_retitle, title_from_message


def test_title_from_message_compacts_whitespace() -> None:
    assert title_from_message("  What is  RAG ?  ") == "What is RAG ?"


def test_title_from_message_truncates_long_input() -> None:
    title = title_from_message("word " * 40, max_len=20)
    assert len(title) <= 20
    assert title.endswith("…")


def test_title_from_blank_falls_back() -> None:
    assert title_from_message("   ") == "New chat"


def test_should_retitle_only_defaults() -> None:
    assert should_retitle("New chat")
    assert should_retitle("Agent chat")
    assert not should_retitle("What is 12 * (3 + 4)?")


def test_production_settings_reject_fake_providers() -> None:
    settings = Settings()
    object.__setattr__(settings, "app_env", "production")
    object.__setattr__(settings, "dev_fake_llm", True)
    object.__setattr__(settings, "dev_fake_embeddings", False)
    object.__setattr__(settings, "gemini_api_key", "test-key")
    object.__setattr__(settings, "database_url", "postgresql://user:pass@localhost:5432/db")
    try:
        settings.validate_runtime()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "DEV_FAKE" in str(exc)


def test_production_settings_require_database() -> None:
    settings = Settings()
    object.__setattr__(settings, "app_env", "production")
    object.__setattr__(settings, "dev_fake_llm", False)
    object.__setattr__(settings, "dev_fake_embeddings", False)
    object.__setattr__(settings, "gemini_api_key", "test-key")
    object.__setattr__(settings, "llm_api_key", None)
    object.__setattr__(settings, "database_url", None)
    try:
        settings.validate_runtime()
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "DATABASE_URL" in str(exc)


def test_development_settings_allow_missing_database() -> None:
    settings = Settings()
    object.__setattr__(settings, "app_env", "development")
    object.__setattr__(settings, "database_url", None)
    settings.validate_runtime()
