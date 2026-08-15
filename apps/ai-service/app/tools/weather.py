"""Weather tool: extract a place, then call a WeatherProvider with retries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.providers.weather import WeatherProvider, WeatherSnapshot
from app.tools.errors import ToolError

# Representative city when the user names a country rather than a city.
_COUNTRY_CITIES: dict[str, str] = {
    "ireland": "Dublin",
    "republic of ireland": "Dublin",
    "united kingdom": "London",
    "uk": "London",
    "britain": "London",
    "great britain": "London",
    "england": "London",
    "scotland": "Edinburgh",
    "wales": "Cardiff",
    "united states": "Washington",
    "united states of america": "Washington",
    "usa": "Washington",
    "us": "Washington",
    "america": "Washington",
    "france": "Paris",
    "germany": "Berlin",
    "italy": "Rome",
    "spain": "Madrid",
    "portugal": "Lisbon",
    "netherlands": "Amsterdam",
    "belgium": "Brussels",
    "sweden": "Stockholm",
    "norway": "Oslo",
    "denmark": "Copenhagen",
    "finland": "Helsinki",
    "poland": "Warsaw",
    "japan": "Tokyo",
    "south korea": "Seoul",
    "china": "Beijing",
    "india": "New Delhi",
    "canada": "Ottawa",
    "australia": "Canberra",
    "new zealand": "Wellington",
    "brazil": "Brasilia",
    "mexico": "Mexico City",
    "egypt": "Cairo",
    "turkey": "Ankara",
    "uae": "Abu Dhabi",
    "united arab emirates": "Abu Dhabi",
    "saudi arabia": "Riyadh",
}

_FILLER = re.compile(
    r"\b(today|tomorrow|tonight|currently|right now|this week|now|please|currently)\b",
    re.IGNORECASE,
)
_ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_TRAILING_PUNCT = re.compile(r"[?.!,;]+$")
_LOCATION_AFTER_PREP = re.compile(
    r"\b(?:weather|forecast|temperature|humidity|wind)\b.*?\b(?:in|for|at)\s+"
    r"(.+?)(?=\s+(?:now|today|tonight|tomorrow|currently|please|right now)\b|[?.!,;]|$)",
    re.IGNORECASE,
)
_LOCATION_GENERIC = re.compile(
    r"\b(?:in|for|at)\s+(.+?)(?=\s+(?:now|today|tonight|tomorrow|currently|please)\b|"
    r"\s+(?:weather|forecast)\b|[?.!,;]|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class WeatherRequest:
    location: str | None
    when: date | None
    raw_query: str


def parse_weather_request(text: str) -> WeatherRequest:
    raw = text.strip()
    when = _parse_when(raw)
    location = _parse_location(raw)
    return WeatherRequest(location=location, when=when, raw_query=raw)


def location_candidates(text: str, location_override: str | None = None) -> list[str]:
    """Build geocoding attempts from the user text, cleaned of time-filler words."""
    parsed = parse_weather_request(text).location
    ordered: list[str] = []
    for raw in (location_override, parsed):
        cleaned = _clean_location(raw or "")
        _add_unique(ordered, cleaned)
        if cleaned and "," in cleaned:
            _add_unique(ordered, cleaned.split(",", maxsplit=1)[0].strip())
        capital = _COUNTRY_CITIES.get(cleaned.lower())
        if capital:
            _add_unique(ordered, capital)
    return ordered


async def lookup_weather(
    *,
    provider: WeatherProvider,
    text: str,
    location_override: str | None = None,
) -> WeatherSnapshot:
    request = parse_weather_request(text)
    candidates = location_candidates(text, location_override)
    if not candidates:
        raise ToolError(
            "I can check the weather, but I need a location. "
            "Try “weather in Boston” or “forecast for Tokyo tomorrow.”",
            code="LOCATION_REQUIRED",
        )

    last_attempt = candidates[0]
    for candidate in candidates:
        last_attempt = candidate
        snapshot = await provider.lookup(location=candidate, when=request.when)
        if snapshot is not None:
            return snapshot

    raise ToolError(
        f"I couldn't resolve “{last_attempt}” to a weather location. "
        "Try a city name, optionally with a country.",
        code="LOCATION_UNRESOLVED",
    )


def format_weather_answer(snapshot: WeatherSnapshot) -> str:
    lines = [
        "This answer uses an external weather tool, not your uploaded documents.",
        "",
        f"**{snapshot.location_name}** — "
        + (
            "current conditions"
            if snapshot.kind == "current"
            else f"forecast for {snapshot.observed_at}"
        ),
    ]
    if snapshot.kind == "current":
        if snapshot.temperature_c is not None:
            lines.append(f"- Temperature: {snapshot.temperature_c:.1f}°C")
        lines.append(f"- Conditions: {snapshot.description}")
        if snapshot.wind_speed_kmh is not None:
            lines.append(f"- Wind: {snapshot.wind_speed_kmh:.0f} km/h")
        if snapshot.humidity_percent is not None:
            lines.append(f"- Humidity: {snapshot.humidity_percent:.0f}%")
    else:
        if snapshot.temperature_max_c is not None and snapshot.temperature_min_c is not None:
            lines.append(
                f"- High / low: {snapshot.temperature_max_c:.1f}°C / "
                f"{snapshot.temperature_min_c:.1f}°C"
            )
        lines.append(f"- Conditions: {snapshot.description}")
    lines.append("")
    lines.append(f"Source: {snapshot.provider} (as of {snapshot.observed_at}).")
    return "\n".join(lines)


def _parse_when(text: str) -> date | None:
    lowered = text.lower()
    iso = _ISO_DATE.search(text)
    if iso:
        try:
            parsed = date.fromisoformat(iso.group(1))
        except ValueError:
            return None
        today = date.today()
        if parsed < today:
            raise ToolError(
                "I can look up current conditions or upcoming forecasts, not past dates.",
                code="DATE_IN_PAST",
            )
        if (parsed - today).days > 16:
            raise ToolError(
                "That date is beyond the available forecast range (about 16 days).",
                code="DATE_OUT_OF_RANGE",
            )
        return parsed if parsed != today else None
    if "tomorrow" in lowered:
        return date.today() + timedelta(days=1)
    return None


def _parse_location(text: str) -> str | None:
    stripped = _ISO_DATE.sub(" ", text)
    for pattern in (_LOCATION_AFTER_PREP, _LOCATION_GENERIC):
        match = pattern.search(stripped)
        if not match:
            continue
        candidate = _clean_location(match.group(1))
        if _looks_like_location(candidate):
            return candidate
    return None


def _clean_location(value: str) -> str:
    cleaned = _TRAILING_PUNCT.sub("", value.strip())
    cleaned = _FILLER.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    return cleaned


def _looks_like_location(value: str) -> bool:
    if len(value) < 2 or len(value) > 80:
        return False
    if re.fullmatch(r"[\d\s+\-*/().]+", value):
        return False
    lowered = value.lower()
    if lowered in {"the", "it", "there", "here", "me"}:
        return False
    return any(ch.isalpha() for ch in value)


def _add_unique(items: list[str], value: str) -> None:
    if not value:
        return
    lowered = value.lower()
    if any(existing.lower() == lowered for existing in items):
        return
    items.append(value)
