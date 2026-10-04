"""Pydantic models and validation for AI suggestions."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.form_schema import FIELDS_BY_ID

TAXON_VALUES = frozenset({"plant", "animal", "fungus", "other", "unsure"})
CONFIDENCE_CAPS: dict[str, float] = {
    "water_flow": 0.6,  # A/B/C from stills; D (dry) may stay higher after validate
    "channel_form": 0.6,
}


class FieldSuggestion(BaseModel):
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("reason must be non-empty")
        return cleaned


class RoleAnalysisResult(BaseModel):
    role: str
    suggestions: dict[str, FieldSuggestion]
    note: str | None = None  # e.g. per-photo quality or upstream_vs_downstream draft
    image_usable: bool = True


INVALID = FieldSuggestion(
    value="not_sure",
    confidence=0.0,
    reason="AI output invalid",
)


def allowed_values_for(field_id: str) -> list[str] | None:
    if field_id == "possible_taxon_group":
        return sorted(TAXON_VALUES)
    field = FIELDS_BY_ID.get(field_id)
    if field is None or field.values is None:
        return None
    return list(field.values)


def normalize_suggestion(field_id: str, raw: Any) -> FieldSuggestion:
    """Validate one field suggestion; invalid → not_sure / 0 / 'AI output invalid'."""
    if not isinstance(raw, dict):
        return INVALID.model_copy()
    try:
        suggestion = FieldSuggestion.model_validate(raw)
    except Exception:
        return INVALID.model_copy()

    allowed = allowed_values_for(field_id)
    if allowed is not None and suggestion.value not in allowed:
        return INVALID.model_copy()

    confidence = suggestion.confidence
    if field_id == "water_flow" and suggestion.value in {"A", "B", "C"}:
        confidence = min(confidence, CONFIDENCE_CAPS["water_flow"])
    elif field_id == "channel_form":
        confidence = min(confidence, CONFIDENCE_CAPS["channel_form"])

    return FieldSuggestion(
        value=suggestion.value,
        confidence=confidence,
        reason=suggestion.reason,
    )


def strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_model_json(text: str) -> dict[str, Any]:
    cleaned = strip_json_fences(text)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("AI JSON root must be an object")
    return data


def validate_role_payload(role: str, field_ids: list[str], data: dict[str, Any]) -> RoleAnalysisResult:
    suggestions: dict[str, FieldSuggestion] = {}
    for field_id in field_ids:
        suggestions[field_id] = normalize_suggestion(field_id, data.get(field_id))

    note = None
    raw_note = data.get("upstream_vs_downstream")
    if isinstance(raw_note, str) and raw_note.strip():
        note = raw_note.strip()

    image_usable = True
    quality = data.get("image_quality")
    if isinstance(quality, dict) and quality.get("usable") is False:
        image_usable = False

    return RoleAnalysisResult(
        role=role,
        suggestions=suggestions,
        note=note,
        image_usable=image_usable,
    )
