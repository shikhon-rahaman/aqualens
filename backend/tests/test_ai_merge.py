"""AI merge rules, validation, and mock analyze tests (no live Groq)."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from app.ai.cache_provider import CachedProvider
from app.ai.chain import ProviderChain
from app.ai.merge import merge_stream_pair
from app.ai.mock_provider import MockProvider
from app.ai.models import (
    FieldSuggestion,
    RoleAnalysisResult,
    normalize_suggestion,
    parse_model_json,
    validate_role_payload,
)
from app.ai.service import analyze_photos
from app.config import get_settings
from app.routers.analyze import get_chain


def _jpeg(width: int = 640, height: int = 480, color: tuple[int, int, int] = (40, 100, 160)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _sug(value: str, confidence: float, reason: str = "visible detail") -> FieldSuggestion:
    return FieldSuggestion(value=value, confidence=confidence, reason=reason)


def _role(role: str, mapping: dict[str, FieldSuggestion]) -> RoleAnalysisResult:
    return RoleAnalysisResult(role=role, suggestions=mapping, image_usable=True)


def test_normalize_invalid_becomes_not_sure():
    result = normalize_suggestion("water_aspect", {"value": "Z", "confidence": 0.9, "reason": "x"})
    assert result.value == "not_sure"
    assert result.confidence == 0.0
    assert result.reason == "AI output invalid"

    result = normalize_suggestion("water_aspect", "not-an-object")
    assert result.value == "not_sure"
    assert result.reason == "AI output invalid"

    result = normalize_suggestion(
        "water_aspect", {"value": "A", "confidence": 0.9, "reason": "   "}
    )
    assert result.value == "not_sure"


def test_confidence_cap_for_flow_and_channel():
    flow = normalize_suggestion(
        "water_flow", {"value": "A", "confidence": 0.95, "reason": "looks fast"}
    )
    assert flow.confidence <= 0.6
    dry = normalize_suggestion(
        "water_flow", {"value": "D", "confidence": 0.9, "reason": "dry bed"}
    )
    assert dry.confidence == 0.9


def test_merge_agree_keeps_lower_confidence():
    up = _role(
        "upstream",
        {"water_aspect": _sug("A", 0.8), "draining_pipes": _sug("no", 0.5)},
    )
    down = _role(
        "downstream",
        {"water_aspect": _sug("A", 0.4), "draining_pipes": _sug("no", 0.6)},
    )
    merged, note, hints = merge_stream_pair(up, down)
    assert merged["water_aspect"].value == "A"
    assert merged["water_aspect"].confidence == 0.4
    assert hints == []


def test_merge_disagree_returns_not_sure():
    up = _role("upstream", {"water_aspect": _sug("A", 0.8)})
    down = _role("downstream", {"water_aspect": _sug("B", 0.7)})
    merged, note, hints = merge_stream_pair(up, down)
    assert merged["water_aspect"].value == "not_sure"
    assert merged["water_aspect"].reason == "upstream and downstream photos differ"
    assert note is not None


def test_merge_yes_wins_and_needs_expert():
    # draining_pipes / sewage_discharge are Group A (stream photos).
    # construction is Group B (context photo) — covered in analyze_photos tests.
    up = _role(
        "upstream",
        {
            "draining_pipes": _sug("yes", 0.55, "pipe visible on bank"),
            "sewage_discharge": _sug("no", 0.4),
            "water_aspect": _sug("A", 0.5),
        },
    )
    down = _role(
        "downstream",
        {
            "draining_pipes": _sug("no", 0.7),
            "sewage_discharge": _sug("yes", 0.6, "discharge visible"),
            "water_aspect": _sug("A", 0.5),
        },
    )
    merged, _note, hints = merge_stream_pair(up, down)
    assert merged["draining_pipes"].value == "yes"
    assert merged["sewage_discharge"].value == "yes"
    assert "draining_pipes" in hints
    assert "sewage_discharge" in hints


def test_validate_role_payload_fills_invalid_fields():
    payload = {
        "water_aspect": {"value": "A", "confidence": 0.8, "reason": "clear"},
        "water_flow": {"value": "QQ", "confidence": 0.9, "reason": "bad"},
    }
    result = validate_role_payload(
        "upstream",
        ["water_aspect", "water_flow"],
        payload,
    )
    assert result.suggestions["water_aspect"].value == "A"
    assert result.suggestions["water_flow"].value == "not_sure"
    assert result.suggestions["water_flow"].reason == "AI output invalid"


def test_parse_strips_markdown_fences():
    data = parse_model_json('```json\n{"water_aspect": {"value": "A", "confidence": 0.5, "reason": "ok"}}\n```')
    assert data["water_aspect"]["value"] == "A"


def test_mock_provider_deterministic(tmp_path: Path):
    mock = MockProvider()
    image = _jpeg()
    a = mock.analyze(image, "upstream")
    b = mock.analyze(image, "upstream")
    assert a.suggestions["water_aspect"].value == b.suggestions["water_aspect"].value


def test_cache_roundtrip(tmp_path: Path):
    cache = CachedProvider(tmp_path / "ai")
    mock = MockProvider()
    image = _jpeg()
    result = mock.analyze(image, "context")
    cache.put(image, "context", result)
    hit = cache.get(image, "context")
    assert hit is not None
    assert hit.suggestions["construction"].value == result.suggestions["construction"].value


def test_chain_uses_mock_without_groq(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "mock")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SLEEP_SECONDS", "0")
    get_settings.cache_clear()
    settings = get_settings()
    chain = ProviderChain(settings=settings)
    result, name = chain.analyze(_jpeg(), "biodiversity")
    assert name == "mock"
    assert result is not None
    assert "possible_taxon_group" in result.suggestions
    get_settings.cache_clear()


def test_analyze_photos_merge_with_mock_overrides(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "mock")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SLEEP_SECONDS", "0")
    get_settings.cache_clear()
    settings = get_settings()

    overrides = {
        "upstream": {
            "water_aspect": _sug("A", 0.9),
            "draining_pipes": _sug("no", 0.5),
            "sewage_discharge": _sug("no", 0.5),
            "construction": _sug("no", 0.5),
            "water_flow": _sug("B", 0.4),
            "bottom_type": _sug("A", 0.5),
            "bank_type": _sug("A", 0.5),
            "channel_form": _sug("B", 0.4),
            "barriers": _sug("no", 0.5),
            "water_withdrawal": _sug("no", 0.5),
            "habitats_present": _sug("not_sure", 0.2),
            "natural_debris_present": _sug("not_sure", 0.2),
        },
        "downstream": {
            "water_aspect": _sug("B", 0.8),
            "draining_pipes": _sug("yes", 0.6, "pipe on bank"),
            "sewage_discharge": _sug("no", 0.5),
            "construction": _sug("no", 0.5),
            "water_flow": _sug("B", 0.4),
            "bottom_type": _sug("A", 0.5),
            "bank_type": _sug("A", 0.5),
            "channel_form": _sug("B", 0.4),
            "barriers": _sug("no", 0.5),
            "water_withdrawal": _sug("no", 0.5),
            "habitats_present": _sug("not_sure", 0.2),
            "natural_debris_present": _sug("not_sure", 0.2),
        },
    }
    chain = ProviderChain(settings=settings, mock=MockProvider(overrides=overrides))
    payload = analyze_photos(
        {"upstream": _jpeg(color=(10, 20, 30)), "downstream": _jpeg(color=(200, 100, 50))},
        chain=chain,
        settings=settings,
        sleep_between=False,
    )
    assert payload["status"] == "ok"
    assert payload["suggestions"]["water_aspect"]["value"] == "not_sure"
    assert payload["suggestions"]["draining_pipes"]["value"] == "yes"
    assert "draining_pipes" in payload["needs_expert_hints"]
    get_settings.cache_clear()


def test_analyze_photos_construction_yes_needs_expert(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "mock")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SLEEP_SECONDS", "0")
    get_settings.cache_clear()
    settings = get_settings()

    overrides = {
        "context": {
            "impervious_left": _sug("no", 0.5),
            "impervious_right": _sug("no", 0.5),
            "vegetation_left": _sug("yes", 0.5),
            "vegetation_right": _sug("yes", 0.5),
            "veg_type_left": _sug("A", 0.4),
            "veg_type_right": _sug("A", 0.4),
            "construction": _sug("yes", 0.7, "works visible in context photo"),
        },
    }
    chain = ProviderChain(settings=settings, mock=MockProvider(overrides=overrides))
    payload = analyze_photos(
        {"context": _jpeg(color=(90, 90, 90))},
        chain=chain,
        settings=settings,
        sleep_between=False,
    )
    assert payload["status"] == "ok"
    assert payload["suggestions"]["construction"]["value"] == "yes"
    assert "construction" in payload["needs_expert_hints"]
    get_settings.cache_clear()


def test_analyze_photos_ai_unavailable_when_chain_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SLEEP_SECONDS", "0")
    get_settings.cache_clear()
    settings = get_settings()
    chain = ProviderChain(settings=settings)
    payload = analyze_photos(
        {"upstream": _jpeg()},
        chain=chain,
        settings=settings,
        sleep_between=False,
    )
    assert payload["status"] == "ai_unavailable"
    assert payload["suggestions"] == {}
    assert "manually" in payload["message"].lower()
    get_settings.cache_clear()


def test_analyze_endpoint_never_saves(client, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER_CHAIN", "mock")
    monkeypatch.setenv("AI_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("SLEEP_SECONDS", "0")
    get_settings.cache_clear()

    # Rebind chain dependency to pick up env.
    app = client.app
    app.dependency_overrides[get_chain] = lambda: ProviderChain(settings=get_settings())

    image = _jpeg()
    before = client.get("/api/observations").json()["observations"]
    response = client.post(
        "/api/analyze",
        files={"photo_upstream": ("up.jpg", image, "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert "water_aspect" in body["suggestions"]
    after = client.get("/api/observations").json()["observations"]
    assert len(after) == len(before)

    app.dependency_overrides.pop(get_chain, None)
    get_settings.cache_clear()
