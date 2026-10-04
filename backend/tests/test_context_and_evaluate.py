"""Weather and water-check adapters (mocked HTTP; no live network)."""

from __future__ import annotations

import httpx
import pytest

from app.context.water_check import check_waterway_nearby
from app.context.weather import clear_weather_cache, fetch_weather
from app.evaluation import evaluate_observation


def test_weather_parses_and_caches():
    clear_weather_cache()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200,
            json={
                "current": {"temperature_2m": 27.5},
                "hourly": {"precipitation": [0.5] * 60},
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        a = fetch_weather(12.97, 77.59, client=client, now=0.0)
        b = fetch_weather(12.97, 77.59, client=client, now=10.0)
    assert a.ok and b.ok
    assert a.temperature_c == 27.5
    assert a.rainfall_48h_mm == pytest.approx(24.0)  # last 48 of 60 × 0.5
    assert calls["n"] == 1  # second call served from cache
    clear_weather_cache()


def test_weather_failure_graceful():
    clear_weather_cache()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="nope")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        snap = fetch_weather(1.0, 2.0, client=client, now=0.0)
    assert snap.ok is False
    assert snap.rainfall_48h_mm is None
    assert snap.temperature_c is None
    clear_weather_cache()


def test_water_nearby_yes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"elements": [{"type": "way", "id": 1}]})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = check_waterway_nearby(12.97, 77.59, client=client)
    assert result.water_nearby == "yes"


def test_water_nearby_no():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"elements": []})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = check_waterway_nearby(12.97, 77.59, client=client)
    assert result.water_nearby == "no"


def test_water_failure_is_unknown_never_flags():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = check_waterway_nearby(12.97, 77.59, client=client)
    assert result.water_nearby == "unknown"

    payload = evaluate_observation(
        {"water_aspect": "A"},
        site_lat=12.97,
        site_lon=77.59,
        fetch_weather_fn=lambda lat, lon: __import__(
            "app.context.weather", fromlist=["WeatherSnapshot"]
        ).WeatherSnapshot(None, None, False, "down"),
        check_water_fn=lambda lat, lon: result,
    )
    assert payload["context"]["water_nearby"] == "unknown"
    assert all(f["code"] != "no_waterway" for f in payload["flags"])


def test_evaluate_endpoint(client, monkeypatch):
    from app.context.weather import WeatherSnapshot
    from app.context.water_check import WaterCheckResult
    import app.evaluation as evaluation_mod

    monkeypatch.setattr(
        evaluation_mod,
        "fetch_weather",
        lambda lat, lon, **kwargs: WeatherSnapshot(5.0, 26.0, True),
    )
    monkeypatch.setattr(
        evaluation_mod,
        "check_waterway_nearby",
        lambda lat, lon, **kwargs: WaterCheckResult("yes"),
    )

    sites = client.get("/api/sites").json()["sites"]
    site_id = sites[0]["id"]
    response = client.post(
        "/api/observations/evaluate",
        json={
            "site_id": site_id,
            "user_lat": sites[0]["lat"],
            "user_lon": sites[0]["lon"],
            "answers": {
                "water_flow": "D",
                "water_height": 15,
                "draining_pipes": "yes",
                "overall_assessment": "good",
            },
            "include_context": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    codes = {f["code"] for f in body["flags"]}
    assert "dry_vs_height" in codes
    assert "expert_draining_pipes" in codes
    assert body["needs_expert"] is True
    assert body["risk"]["disclaimer"].startswith("Indicative only")
    assert body["context"]["rainfall_48h_mm"] == 5.0
    assert body["context"]["water_nearby"] == "yes"


def test_create_observation_runs_evaluation(client):
    sites = client.get("/api/sites").json()["sites"]
    site_id = sites[0]["id"]
    response = client.post(
        "/api/observations/json",
        json={
            "site_id": site_id,
            "answers": {
                "construction": "yes",
                "overall_assessment": "moderate",
            },
            "field_sources": {
                "construction": "human",
                "overall_assessment": "human",
            },
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["needs_expert"] is True
    assert body["status"] == "flagged"
    assert body["risk_contact"] is not None
    assert body["risk_ecosystem"] is not None
    assert any(f["code"] == "expert_construction" for f in body["flags"])
