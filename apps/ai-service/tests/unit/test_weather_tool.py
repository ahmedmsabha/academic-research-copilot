"""Unit tests for weather location extraction and retry."""

from __future__ import annotations

import pytest

from app.providers.weather import FakeWeatherProvider
from app.tools.errors import ToolError
from app.tools.weather import location_candidates, lookup_weather, parse_weather_request


def test_strips_now_from_country_query() -> None:
    request = parse_weather_request("What is the weather in Ireland now?")
    assert request.location == "Ireland"
    assert request.when is None


def test_country_adds_capital_candidate() -> None:
    candidates = location_candidates("What is the weather in Ireland now?")
    assert candidates[0] == "Ireland"
    assert "Dublin" in candidates
    assert "Ireland now" not in candidates


async def test_lookup_retries_after_dirty_location() -> None:
    provider = FakeWeatherProvider()
    snapshot = await lookup_weather(
        provider=provider,
        text="What is the weather in Ireland now?",
        location_override="Ireland now",
    )
    assert snapshot is not None
    attempted = [location for location, _when in provider.calls]
    assert "Ireland now" not in attempted
    assert "Ireland" in attempted or "Dublin" in attempted


async def test_unresolved_location_still_fails() -> None:
    provider = FakeWeatherProvider()
    with pytest.raises(ToolError) as exc:
        await lookup_weather(provider=provider, text="weather in unknownville")
    assert "couldn't resolve" in exc.value.message.lower()
