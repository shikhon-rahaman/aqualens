"""Open-Meteo weather adapter: last 48h rainfall sum and current temperature."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_TIMEOUT_S = 8.0
CACHE_TTL_S = 3600.0

_cache: dict[str, tuple[float, "WeatherSnapshot"]] = {}


@dataclass(frozen=True)
class WeatherSnapshot:
    rainfall_48h_mm: float | None
    temperature_c: float | None
    ok: bool
    error: str | None = None


def _cache_key(lat: float, lon: float) -> str:
    return f"{lat:.3f},{lon:.3f}"


def clear_weather_cache() -> None:
    _cache.clear()


def fetch_weather(
    lat: float,
    lon: float,
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    client: httpx.Client | None = None,
    now: float | None = None,
) -> WeatherSnapshot:
    """Fetch weather with 1-hour in-memory cache. Failures return ok=False."""
    key = _cache_key(lat, lon)
    clock = time.monotonic() if now is None else now
    cached = _cache.get(key)
    if cached is not None:
        expires_at, snap = cached
        if clock < expires_at:
            return snap

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout_s)
    try:
        snap = _request_weather(http, lat, lon, timeout_s=timeout_s)
        if snap.ok:
            _cache[key] = (clock + CACHE_TTL_S, snap)
        return snap
    except Exception as exc:
        logger.warning("weather fetch failed: %s", exc)
        return WeatherSnapshot(
            rainfall_48h_mm=None,
            temperature_c=None,
            ok=False,
            error=str(exc),
        )
    finally:
        if owns_client:
            http.close()


def _request_weather(
    http: httpx.Client, lat: float, lon: float, *, timeout_s: float
) -> WeatherSnapshot:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "hourly": "precipitation",
        "past_days": 2,
        "forecast_days": 1,
        "timezone": "UTC",
    }
    response = http.get(OPEN_METEO_URL, params=params, timeout=timeout_s)
    response.raise_for_status()
    data = response.json()
    return _parse_open_meteo(data)


def _parse_open_meteo(data: dict[str, Any]) -> WeatherSnapshot:
    temperature: float | None = None
    current = data.get("current")
    if isinstance(current, dict) and current.get("temperature_2m") is not None:
        try:
            temperature = float(current["temperature_2m"])
        except (TypeError, ValueError):
            temperature = None

    rainfall: float | None = None
    hourly = data.get("hourly")
    if isinstance(hourly, dict):
        precip = hourly.get("precipitation")
        if isinstance(precip, list) and precip:
            # Last 48 hourly samples (past_days=2 + a little forecast buffer).
            window = precip[-48:] if len(precip) >= 48 else precip
            try:
                rainfall = float(sum(float(x or 0) for x in window))
            except (TypeError, ValueError):
                rainfall = None

    return WeatherSnapshot(
        rainfall_48h_mm=rainfall,
        temperature_c=temperature,
        ok=True,
        error=None,
    )
