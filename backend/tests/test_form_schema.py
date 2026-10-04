"""Form schema and answer validation tests."""

from app.form_schema import (
    FIELDS_BY_ID,
    get_form_schema,
    validate_answers,
    validate_feelings,
    validate_field_sources,
)


def test_form_schema_endpoint(client):
    response = client.get("/api/form-schema")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "1"
    ids = {f["id"] for f in payload["fields"]}
    assert "water_aspect" in ids
    assert "habitats_present" in ids
    assert "water_height" in ids
    assert "feelings" in ids
    assert "habitats_present" in payload["pending_notes"]
    assert "water_height" in payload["pending_notes"]


def test_pending_fields_are_presence_or_soft_unit():
    habitats = FIELDS_BY_ID["habitats_present"]
    debris = FIELDS_BY_ID["natural_debris_present"]
    height = FIELDS_BY_ID["water_height"]
    assert habitats.pending is True
    assert habitats.values == ["yes", "no", "not_sure"]
    assert debris.pending is True
    assert debris.values == ["yes", "no", "not_sure"]
    assert height.pending is True
    assert height.value_type == "number"
    assert height.ai_role == "human_only"


def test_validate_answers_rejects_illegal_choice():
    errors = validate_answers({"water_aspect": "Z"})
    assert any("water_aspect" in e for e in errors)


def test_validate_answers_accepts_legal_payload():
    errors = validate_answers(
        {
            "water_aspect": "A",
            "water_flow": "B",
            "habitats_present": "yes",
            "water_height": 42,
            "overall_assessment": "moderate",
        }
    )
    assert errors == []


def test_validate_feelings_range():
    assert validate_feelings(
        {
            "joy": {"value": 3, "na": False},
            "serenity": {"value": None, "na": True},
            "anger": {"value": 1, "na": False},
            "fear": {"value": 5, "na": False},
        }
    ) is None
    assert validate_feelings(
        {
            "joy": {"value": 9, "na": False},
            "serenity": {"value": 3, "na": False},
            "anger": {"value": 3, "na": False},
            "fear": {"value": 3, "na": False},
        }
    )


def test_validate_field_sources():
    errors = validate_field_sources({"water_aspect": "ai_accepted"})
    assert errors == []
    errors = validate_field_sources({"water_aspect": "robot"})
    assert errors


def test_get_form_schema_includes_all_answer_fields():
    schema = get_form_schema()
    choice_ids = [
        f.id for f in schema.fields if f.value_type in {"choice", "number", "feelings", "text"}
    ]
    assert "channel_form" in choice_ids
    assert "invasive_species_notes" in choice_ids
