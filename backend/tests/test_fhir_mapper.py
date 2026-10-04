"""FHIR mapper tests: library validation, snapshot structure, privacy, mocked send.

Offline limits (what we could NOT validate here):
- HAPI server `$validate` OperationOutcome against the live public test server
- Whether custom CodeSystem URLs resolve or are registered on any terminology server
- Post-transaction referential integrity after the server rewrites IDs
- Full R4 vs R4B wire compatibility quirks beyond what fhir.resources R4B models accept
- Search / compartment / authorization rules on the remote FHIR server
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fhir.resources.R4B.bundle import Bundle

from app.adapters.fhir_client import send_bundle
from app.config import Settings, get_settings
from app.fhir_mapper import (
    EXCLUDED_FROM_FHIR,
    FHIR_VERSION_USED,
    assert_bundle_privacy,
    bundle_to_dict,
    fhir_export_payload,
    observation_row_to_bundle,
)

SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "fhir_bundle_structure.json"

FIXED_IDS = {
    "bundle": "bundle-fixed",
    "location": "loc-fixed",
    "obs:water_aspect": "obs-water-aspect",
    "prov:water_aspect": "prov-water-aspect",
    "obs:water_height": "obs-water-height",
    "prov:water_height": "prov-water-height",
    "obs:draining_pipes": "obs-draining-pipes",
    "prov:draining_pipes": "prov-draining-pipes",
    "obs:overall": "obs-overall",
    "obs:risk_contact": "obs-risk-contact",
    "obs:risk_ecosystem": "obs-risk-ecosystem",
}


def _sample_row() -> SimpleNamespace:
    site = SimpleNamespace(
        id="site-1",
        name="Demo Creek North",
        code="DEMO-N",
        lat=12.9716,
        lon=77.5946,
    )
    return SimpleNamespace(
        id="obs-1",
        site=site,
        captured_at=datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc),
        answers_json={
            "water_aspect": "A",
            "water_height": 42,
            "draining_pipes": "yes",
            "overall_assessment": "moderate",
            "invasive_species_notes": "maybe water hyacinth near bridge",
            "feelings": {
                "joy": {"value": 3, "na": False},
                "serenity": {"value": None, "na": True},
                "anger": {"value": 2, "na": False},
                "fear": {"value": 1, "na": False},
            },
        },
        field_sources_json={
            "water_aspect": "ai_accepted",
            "water_height": "human",
            "draining_pipes": "ai_edited",
            "overall_assessment": "human",
        },
        ai_suggestions_json={
            "water_aspect": {
                "value": "A",
                "confidence": 0.8,
                "reason": "Water surface looks clear.",
            },
            "draining_pipes": {
                "value": "yes",
                "confidence": 0.6,
                "reason": "A pipe is visible on the bank.",
            },
        },
        photos_json={"upstream": "/uploads/obs-1/upstream.jpg"},
        feelings_json={
            "joy": {"value": 3, "na": False},
            "serenity": {"value": None, "na": True},
            "anger": {"value": 2, "na": False},
            "fear": {"value": 1, "na": False},
        },
        overall_user="moderate",
        overall_suggested="moderate",
        risk_contact="high",
        risk_ecosystem="moderate",
        risk_reasons_json={
            "contact": ["Draining pipe marked yes"],
            "ecosystem": ["Few ecosystem-pressure signals from the answers"],
            "disclaimer": "Indicative only, not a safety certification",
        },
    )


@pytest.fixture()
def settings() -> Settings:
    get_settings.cache_clear()
    s = Settings(
        fhir_codesystem_url="https://example.org/aqualens/CodeSystem/stream-observation",
        fhir_server_url="https://hapi.fhir.org/baseR4",
    )
    yield s
    get_settings.cache_clear()


def test_fhir_version_is_r4b():
    assert FHIR_VERSION_USED == "R4B"


def test_bundle_validates_with_library(settings: Settings):
    row = _sample_row()
    bundle = observation_row_to_bundle(row, settings, fixed_ids=FIXED_IDS)
    assert isinstance(bundle, Bundle)
    assert bundle.type == "transaction"
    # Round-trip validation
    again = Bundle.model_validate(bundle_to_dict(bundle))
    assert again.type == "transaction"
    assert again.entry is not None
    assert len(again.entry) >= 5


def test_bundle_contains_expected_resource_types(settings: Settings):
    row = _sample_row()
    data = bundle_to_dict(observation_row_to_bundle(row, settings, fixed_ids=FIXED_IDS))
    types = [e["resource"]["resourceType"] for e in data["entry"]]
    assert types.count("Location") == 1
    assert "Observation" in types
    assert "Provenance" in types

    codes = []
    for entry in data["entry"]:
        res = entry["resource"]
        if res["resourceType"] != "Observation":
            continue
        codes.append(res["code"]["coding"][0]["code"])
    assert "water_aspect" in codes
    assert "overall_assessment" in codes
    assert "risk_contact" in codes
    assert "risk_ecosystem" in codes
    assert "feelings" not in codes
    assert "invasive_species_notes" not in codes


def test_provenance_records_field_sources(settings: Settings):
    row = _sample_row()
    data = bundle_to_dict(observation_row_to_bundle(row, settings, fixed_ids=FIXED_IDS))
    activities = []
    for entry in data["entry"]:
        res = entry["resource"]
        if res["resourceType"] != "Provenance":
            continue
        activities.append(res["activity"]["coding"][0]["code"])
    assert "ai_accepted" in activities
    assert "ai_edited" in activities
    assert "human" in activities


def test_privacy_excludes_photos_feelings_free_text(settings: Settings):
    row = _sample_row()
    data = bundle_to_dict(observation_row_to_bundle(row, settings, fixed_ids=FIXED_IDS))
    assert_bundle_privacy(data)
    blob = json.dumps(data)
    assert "/uploads/" not in blob
    assert "invasive_species_notes" not in blob
    assert "water hyacinth" not in blob
    assert '"feelings"' not in blob


def _normalize_for_snapshot(bundle: dict) -> dict:
    """Keep stable structure keys for snapshot comparison."""
    entries = []
    for entry in bundle.get("entry") or []:
        res = entry["resource"]
        item = {
            "request": entry.get("request"),
            "resourceType": res["resourceType"],
        }
        if res["resourceType"] == "Location":
            item["name"] = res.get("name")
            item["position"] = res.get("position")
        elif res["resourceType"] == "Observation":
            item["code"] = res["code"]["coding"][0]["code"]
            if "valueCodeableConcept" in res:
                item["value"] = res["valueCodeableConcept"]["coding"][0]["code"]
            if "valueQuantity" in res:
                item["valueQuantity"] = res["valueQuantity"]["value"]
            if res.get("note"):
                item["has_note"] = True
        elif res["resourceType"] == "Provenance":
            item["activity"] = res["activity"]["coding"][0]["code"]
        entries.append(item)
    return {
        "resourceType": bundle["resourceType"],
        "type": bundle["type"],
        "excluded": list(EXCLUDED_FROM_FHIR),
        "fhir_version": FHIR_VERSION_USED,
        "entry": entries,
    }


def test_bundle_structure_snapshot(settings: Settings):
    row = _sample_row()
    data = bundle_to_dict(observation_row_to_bundle(row, settings, fixed_ids=FIXED_IDS))
    actual = _normalize_for_snapshot(data)
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert actual == expected


def test_fhir_export_endpoint(client, settings: Settings, monkeypatch):
    monkeypatch.setattr("app.routers.observations.get_settings", lambda: settings)
    sites = client.get("/api/sites").json()["sites"]
    site_id = sites[0]["id"]
    created = client.post(
        "/api/observations/json",
        json={
            "site_id": site_id,
            "answers": {
                "water_aspect": "B",
                "overall_assessment": "moderate",
                "invasive_species_notes": "secret free text",
            },
            "field_sources": {
                "water_aspect": "human",
                "overall_assessment": "human",
            },
            "feelings": {
                "joy": {"value": 3, "na": False},
                "serenity": {"value": 3, "na": False},
                "anger": {"value": 3, "na": False},
                "fear": {"value": 3, "na": False},
            },
        },
    )
    assert created.status_code == 201, created.text
    obs_id = created.json()["id"]
    response = client.get(f"/api/observations/{obs_id}/fhir")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fhir_version"] == "R4B"
    assert body["excluded"] == list(EXCLUDED_FROM_FHIR)
    assert body["bundle"]["resourceType"] == "Bundle"
    assert body["bundle"]["type"] == "transaction"
    assert_bundle_privacy(body["bundle"])
    assert "secret free text" not in json.dumps(body)


def test_fhir_send_endpoint_mocked(client, settings: Settings, monkeypatch):
    monkeypatch.setattr("app.routers.observations.get_settings", lambda: settings)

    def fake_send(server_url, bundle, **kwargs):
        assert server_url.endswith("baseR4") or "hapi" in server_url
        assert bundle["resourceType"] == "Bundle"
        return {
            "ok": True,
            "http_status": 200,
            "server_response": {"resourceType": "Bundle", "type": "transaction-response"},
        }

    monkeypatch.setattr("app.routers.observations.send_bundle", fake_send)

    sites = client.get("/api/sites").json()["sites"]
    created = client.post(
        "/api/observations/json",
        json={
            "site_id": sites[0]["id"],
            "answers": {"water_aspect": "A", "overall_assessment": "good"},
            "field_sources": {"water_aspect": "human", "overall_assessment": "human"},
        },
    )
    obs_id = created.json()["id"]
    response = client.post(f"/api/observations/{obs_id}/fhir/send")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["http_status"] == 200
    assert body["fhir_sent_at"] is not None
    assert "photos" in body["excluded"]


def test_send_bundle_client_posts_json():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"resourceType": "Bundle", "type": "transaction-response"},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        result = send_bundle(
            "https://hapi.fhir.org/baseR4",
            {"resourceType": "Bundle", "type": "transaction", "entry": []},
            client=client,
        )
    assert result["ok"] is True
    assert result["http_status"] == 200
    assert seen["body"]["type"] == "transaction"


def test_export_payload_shape(settings: Settings):
    payload = fhir_export_payload(_sample_row(), settings)
    assert set(payload.keys()) >= {"bundle", "excluded", "fhir_version"}
    assert payload["excluded"] == ["photos", "feelings", "free_text"]
