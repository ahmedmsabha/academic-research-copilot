"""Weather provider protocol and Open-Meteo adapter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

import httpx

from app.core.errors import ProviderTimeoutError, ProviderUnavailableError

WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    location_name: str
    country: str | None
    latitude: float
    longitude: float
    kind: str  # "current" | "forecast"
    observed_at: str
    temperature_c: float | None
    temperature_max_c: float | None
    temperature_min_c: float | None
    weather_code: int | None
    description: str
    wind_speed_kmh: float | None
    humidity_percent: float | None
    provider: str


class WeatherProvider(Protocol):
    async def lookup(
        self,
        *,
        location: str,
        when: date | None = None,
    ) -> WeatherSnapshot | None: ...


class OpenMeteoWeatherProvider:
    """Open-Meteo geocoding + forecast. No API key required."""

    provider_name = "open-meteo"
    _geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
    _forecast_url = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, *, timeout_ms: int = 10_000) -> None:
        self._timeout = timeout_ms / 1000

    async def lookup(self, *, location: str, when: date | None = None) -> WeatherSnapshot | None:
        place = location.strip()
        if not place:
            return None
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                geo = await client.get(
                    self._geocode_url,
                    params={"name": place, "count": 1, "language": "en", "format": "json"},
                    headers={"User-Agent": "AcademicResearchCopilot/0.1"},
                )
                geo.raise_for_status()
                geo_payload = geo.json()
                results = geo_payload.get("results") if isinstance(geo_payload, dict) else None
                if not results:
                    return None
                hit = results[0]
                latitude = float(hit["latitude"])
                longitude = float(hit["longitude"])
                name = str(hit.get("name") or place)
                country = hit.get("country")
                admin = hit.get("admin1")
                display = name
                if admin:
                    display = f"{name}, {admin}"
                if country:
                    display = f"{display}, {country}" if admin else f"{name}, {country}"

                params: dict[str, str | float] = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": "auto",
                }
                today = date.today()
                if when is None or when == today:
                    params["current"] = (
                        "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
                    )
                    forecast = await client.get(
                        self._forecast_url,
                        params=params,
                        headers={"User-Agent": "AcademicResearchCopilot/0.1"},
                    )
                    forecast.raise_for_status()
                    payload = forecast.json()
                    current = payload.get("current") if isinstance(payload, dict) else None
                    if not isinstance(current, dict):
                        raise ProviderUnavailableError(
                            "Weather data is unavailable right now. Please try again."
                        )
                    code = current.get("weather_code")
                    weather_code = int(code) if isinstance(code, (int, float)) else None
                    return WeatherSnapshot(
                        location_name=display,
                        country=str(country) if country else None,
                        latitude=latitude,
                        longitude=longitude,
                        kind="current",
                        observed_at=str(current.get("time") or datetime.now(UTC).isoformat()),
                        temperature_c=_as_float(current.get("temperature_2m")),
                        temperature_max_c=None,
                        temperature_min_c=None,
                        weather_code=weather_code,
                        description=_describe(weather_code),
                        wind_speed_kmh=_as_float(current.get("wind_speed_10m")),
                        humidity_percent=_as_float(current.get("relative_humidity_2m")),
                        provider=self.provider_name,
                    )

                params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min"
                params["start_date"] = when.isoformat()
                params["end_date"] = when.isoformat()
                forecast = await client.get(
                    self._forecast_url,
                    params=params,
                    headers={"User-Agent": "AcademicResearchCopilot/0.1"},
                )
                forecast.raise_for_status()
                payload = forecast.json()
                daily = payload.get("daily") if isinstance(payload, dict) else None
                if not isinstance(daily, dict):
                    raise ProviderUnavailableError(
                        "Weather data is unavailable right now. Please try again."
                    )
                codes = daily.get("weather_code") or []
                maxes = daily.get("temperature_2m_max") or []
                mins = daily.get("temperature_2m_min") or []
                weather_code = int(codes[0]) if codes else None
                return WeatherSnapshot(
                    location_name=display,
                    country=str(country) if country else None,
                    latitude=latitude,
                    longitude=longitude,
                    kind="forecast",
                    observed_at=when.isoformat(),
                    temperature_c=None,
                    temperature_max_c=_as_float(maxes[0] if maxes else None),
                    temperature_min_c=_as_float(mins[0] if mins else None),
                    weather_code=weather_code,
                    description=_describe(weather_code),
                    wind_speed_kmh=None,
                    humidity_percent=None,
                    provider=self.provider_name,
                )
        except ProviderUnavailableError:
            raise
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Weather lookup timed out. Please try again.") from exc
        except Exception as exc:  # noqa: BLE001 — map upstream failures safely
            raise ProviderUnavailableError(
                "Weather lookup is temporarily unavailable. Please try again."
            ) from exc


class FakeWeatherProvider:
    """Deterministic weather provider for tests."""

    provider_name = "fake-weather"

    def __init__(self, snapshot: WeatherSnapshot | None = None) -> None:
        self.calls: list[tuple[str, date | None]] = []
        self.snapshot = snapshot or WeatherSnapshot(
            location_name="Paris, Île-de-France, France",
            country="France",
            latitude=48.85,
            longitude=2.35,
            kind="current",
            observed_at="2026-08-14T10:00",
            temperature_c=18.0,
            temperature_max_c=None,
            temperature_min_c=None,
            weather_code=2,
            description="Partly cloudy",
            wind_speed_kmh=12.0,
            humidity_percent=64.0,
            provider=self.provider_name,
        )

    async def lookup(self, *, location: str, when: date | None = None) -> WeatherSnapshot | None:
        self.calls.append((location, when))
        if not location.strip():
            return None
        normalized = location.strip().lower()
        if normalized in {"unknownville", "nowhere"}:
            return None
        if normalized.endswith(" now") or " now " in f" {normalized} ":
            return None
        if when is not None:
            return WeatherSnapshot(
                location_name=self.snapshot.location_name,
                country=self.snapshot.country,
                latitude=self.snapshot.latitude,
                longitude=self.snapshot.longitude,
                kind="forecast",
                observed_at=when.isoformat(),
                temperature_c=None,
                temperature_max_c=22.0,
                temperature_min_c=14.0,
                weather_code=1,
                description="Mainly clear",
                wind_speed_kmh=None,
                humidity_percent=None,
                provider=self.provider_name,
            )
        return self.snapshot


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _describe(code: int | None) -> str:
    if code is None:
        return "Conditions unavailable"
    return WMO_DESCRIPTIONS.get(code, f"Weather code {code}")
