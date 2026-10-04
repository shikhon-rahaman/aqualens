"""Orchestrate validation + risk + context for evaluate / save."""

from __future__ import annotations

from typing import Any, Callable

from app.context.water_check import WaterCheckResult, check_waterway_nearby
from app.context.weather import WeatherSnapshot, fetch_weather
from app.risk import (
    RiskBundle,
    build_risk_bundle,
    overall_mismatch_levels,
    suggest_overall_from_answers,
)
from app.validation import Flag, any_needs_expert, validate_answers_rules

WeatherFetcher = Callable[[float, float], WeatherSnapshot]
WaterChecker = Callable[[float, float], WaterCheckResult]


def evaluate_observation(
    answers: dict[str, Any],
    *,
    ai_suggestions: dict[str, Any] | None = None,
    field_sources: dict[str, str] | None = None,
    site_lat: float | None = None,
    site_lon: float | None = None,
    user_lat: float | None = None,
    user_lon: float | None = None,
    unusable_photos: list[str] | None = None,
    fetch_weather_fn: WeatherFetcher | None = None,
    check_water_fn: WaterChecker | None = None,
    include_context: bool = True,
) -> dict[str, Any]:
    """Dry-run evaluation payload (never persists)."""
    weather: WeatherSnapshot | None = None
    water: WaterCheckResult | None = None

    weather_fn = fetch_weather if fetch_weather_fn is None else fetch_weather_fn
    water_fn = check_waterway_nearby if check_water_fn is None else check_water_fn

    if include_context and site_lat is not None and site_lon is not None:
        weather = weather_fn(site_lat, site_lon)
        water = water_fn(site_lat, site_lon)

    rainfall = weather.rainfall_48h_mm if weather and weather.ok else None
    flags = validate_answers_rules(
        answers,
        ai_suggestions=ai_suggestions,
        field_sources=field_sources,
        site_lat=site_lat,
        site_lon=site_lon,
        user_lat=user_lat,
        user_lon=user_lon,
        unusable_photos=unusable_photos,
    )
    # Water nearby unknown/no must never add a flag (rule enforced by omission).

    suggested, pressure_count = suggest_overall_from_answers(answers)
    user_overall = answers.get("overall_assessment")
    mismatch = overall_mismatch_levels(
        str(user_overall) if user_overall is not None else None,
        suggested,
    )
    risk: RiskBundle = build_risk_bundle(answers, rainfall_48h_mm=rainfall)

    return {
        "flags": [flag.model_dump() for flag in flags],
        "needs_expert": any_needs_expert(flags),
        "overall_suggested": suggested,
        "overall_pressure_count": pressure_count,
        "overall_mismatch_levels": mismatch,
        "risk": risk.model_dump(),
        "context": {
            "rainfall_48h_mm": rainfall,
            "temperature_c": weather.temperature_c if weather and weather.ok else None,
            "water_nearby": water.water_nearby if water else "unknown",
        },
    }


def flags_from_payload(payload: dict[str, Any]) -> list[Flag]:
    return [Flag.model_validate(item) for item in payload.get("flags", [])]
