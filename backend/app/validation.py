"""Pure validation rules from docs/02 section 4.

All thresholds are module constants so they can be tuned without rewriting rules.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.form_schema import WATER_HEIGHT_SOFT_MAX, WATER_HEIGHT_SOFT_MIN
from app.geo import haversine_m
from app.risk import OVERALL_LEVELS, level_index, suggest_overall_from_answers

# Tunable thresholds (documented in tests / Prompt 4 summary).
GPS_FLAG_DISTANCE_M = 500.0
AI_LOW_CONFIDENCE = 0.5
AI_ASPECT_CONFLICT_CONFIDENCE = 0.7
AI_VEGETATION_CONFLICT_CONFIDENCE = 0.7
TURBID_ASPECT_VALUES = frozenset({"B", "C", "D"})
TREE_VEG_TYPE = "C"

Severity = Literal["info", "warning", "error"]


class Flag(BaseModel):
    code: str
    fields: list[str] = Field(default_factory=list)
    message: str
    severity: Severity
    needs_expert: bool = False


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ai_entry(ai_suggestions: dict[str, Any], field_id: str) -> dict[str, Any] | None:
    raw = ai_suggestions.get(field_id)
    return raw if isinstance(raw, dict) else None


def _ai_value(ai_suggestions: dict[str, Any], field_id: str) -> str | None:
    entry = _ai_entry(ai_suggestions, field_id)
    if entry is None:
        return None
    value = entry.get("value")
    return str(value) if value is not None else None


def _ai_confidence(ai_suggestions: dict[str, Any], field_id: str) -> float | None:
    entry = _ai_entry(ai_suggestions, field_id)
    if entry is None:
        return None
    try:
        return float(entry.get("confidence"))
    except (TypeError, ValueError):
        return None


def validate_answers_rules(
    answers: dict[str, Any],
    *,
    ai_suggestions: dict[str, Any] | None = None,
    field_sources: dict[str, str] | None = None,
    site_lat: float | None = None,
    site_lon: float | None = None,
    user_lat: float | None = None,
    user_lon: float | None = None,
    unusable_photos: list[str] | None = None,
    gps_flag_distance_m: float = GPS_FLAG_DISTANCE_M,
) -> list[Flag]:
    """Run every docs/02 §4 rule. Pure: no I/O."""
    ai_suggestions = ai_suggestions or {}
    field_sources = field_sources or {}
    flags: list[Flag] = []

    flags.extend(_rule_dry_vs_height(answers))
    flags.extend(_rule_sewage_without_pipes(answers))
    flags.extend(_rule_clear_vs_ai_turbid(answers, ai_suggestions))
    flags.extend(_rule_water_height_range(answers))
    flags.extend(_rule_veg_type_without_presence(answers))
    flags.extend(_rule_ai_trees_vs_no_veg(answers, ai_suggestions))
    flags.extend(_rule_expert_triggers(answers))
    flags.extend(_rule_low_ai_confidence(ai_suggestions, field_sources, answers))
    flags.extend(_rule_unusable_photos(unusable_photos or []))
    flags.extend(
        _rule_gps_distance(
            site_lat=site_lat,
            site_lon=site_lon,
            user_lat=user_lat,
            user_lon=user_lon,
            max_m=gps_flag_distance_m,
        )
    )
    flags.extend(_rule_overall_mismatch(answers))
    return flags


def any_needs_expert(flags: list[Flag]) -> bool:
    return any(flag.needs_expert for flag in flags)


def _rule_dry_vs_height(answers: dict[str, Any]) -> list[Flag]:
    height = _num(answers.get("water_height"))
    if answers.get("water_flow") == "D" and height is not None and height > 0:
        return [
            Flag(
                code="dry_vs_height",
                fields=["water_flow", "water_height"],
                message=(
                    "Flow is marked dry but water height is greater than zero. "
                    "Please recheck one of these answers."
                ),
                severity="error",
                needs_expert=False,
            )
        ]
    return []


def _rule_sewage_without_pipes(answers: dict[str, Any]) -> list[Flag]:
    if answers.get("sewage_discharge") == "yes" and answers.get("draining_pipes") == "no":
        return [
            Flag(
                code="sewage_without_pipes",
                fields=["sewage_discharge", "draining_pipes"],
                message=(
                    "Sewage discharge is marked yes but draining pipes are marked no. "
                    "Please recheck both answers."
                ),
                severity="warning",
                needs_expert=False,
            )
        ]
    return []


def _rule_clear_vs_ai_turbid(
    answers: dict[str, Any], ai_suggestions: dict[str, Any]
) -> list[Flag]:
    if answers.get("water_aspect") != "A":
        return []
    ai_val = _ai_value(ai_suggestions, "water_aspect")
    conf = _ai_confidence(ai_suggestions, "water_aspect")
    if (
        ai_val in TURBID_ASPECT_VALUES
        and conf is not None
        and conf >= AI_ASPECT_CONFLICT_CONFIDENCE
    ):
        return [
            Flag(
                code="clear_vs_ai_turbid",
                fields=["water_aspect"],
                message=(
                    "You marked the water as clear, but the AI saw turbidity, foam, "
                    "or altered colour with high confidence. Please recheck the photo."
                ),
                severity="warning",
                needs_expert=False,
            )
        ]
    return []


def _rule_water_height_range(answers: dict[str, Any]) -> list[Flag]:
    if "water_height" not in answers or answers.get("water_height") is None:
        return []
    height = _num(answers.get("water_height"))
    if height is None:
        return [
            Flag(
                code="water_height_invalid",
                fields=["water_height"],
                message="Water height must be a number (cm unit to be confirmed).",
                severity="warning",
                needs_expert=False,
            )
        ]
    if height < WATER_HEIGHT_SOFT_MIN or height > WATER_HEIGHT_SOFT_MAX:
        return [
            Flag(
                code="water_height_out_of_range",
                fields=["water_height"],
                message=(
                    f"Water height {height} looks outside the soft plausible range "
                    f"({WATER_HEIGHT_SOFT_MIN:g}–{WATER_HEIGHT_SOFT_MAX:g} cm, unit to confirm)."
                ),
                severity="warning",
                needs_expert=False,
            )
        ]
    return []


def _rule_veg_type_without_presence(answers: dict[str, Any]) -> list[Flag]:
    flags: list[Flag] = []
    for side in ("left", "right"):
        veg = answers.get(f"vegetation_{side}")
        veg_type = answers.get(f"veg_type_{side}")
        if veg == "no" and veg_type not in (None, "", "not_sure"):
            flags.append(
                Flag(
                    code=f"veg_type_without_presence_{side}",
                    fields=[f"vegetation_{side}", f"veg_type_{side}"],
                    message=(
                        f"Vegetation on the image-{side} is marked no, but a vegetation "
                        "type is still set. Clear the type or change vegetation to yes."
                    ),
                    severity="error",
                    needs_expert=False,
                )
            )
    return flags


def _rule_ai_trees_vs_no_veg(
    answers: dict[str, Any], ai_suggestions: dict[str, Any]
) -> list[Flag]:
    flags: list[Flag] = []
    for side in ("left", "right"):
        if answers.get(f"vegetation_{side}") != "no":
            continue
        type_field = f"veg_type_{side}"
        veg_field = f"vegetation_{side}"
        ai_type = _ai_value(ai_suggestions, type_field)
        conf_type = _ai_confidence(ai_suggestions, type_field)
        ai_veg = _ai_value(ai_suggestions, veg_field)
        conf_veg = _ai_confidence(ai_suggestions, veg_field)

        trees = (
            ai_type == TREE_VEG_TYPE
            and conf_type is not None
            and conf_type >= AI_VEGETATION_CONFLICT_CONFIDENCE
        )
        dense_veg = (
            ai_veg == "yes"
            and conf_veg is not None
            and conf_veg >= AI_VEGETATION_CONFLICT_CONFIDENCE
            and ai_type == TREE_VEG_TYPE
        )
        if trees or dense_veg:
            flags.append(
                Flag(
                    code=f"ai_trees_vs_no_veg_{side}",
                    fields=[veg_field, type_field],
                    message=(
                        f"You marked no vegetation on the image-{side}, but the AI "
                        "saw trees or dense bank vegetation with high confidence."
                    ),
                    severity="warning",
                    needs_expert=False,
                )
            )
    return flags


def _rule_expert_triggers(answers: dict[str, Any]) -> list[Flag]:
    flags: list[Flag] = []
    triggers = (
        ("draining_pipes", "yes", "A draining pipe was marked yes, so an expert should review."),
        ("sewage_discharge", "yes", "Sewage discharge was marked yes, so an expert should review."),
        ("construction", "yes", "Construction in the stream was marked yes, so an expert should review."),
        ("vegetation_cuts", "yes", "Recent vegetation cuts were marked yes, so an expert should review."),
        ("invasive_species", "yes", "Possible invasive plants were marked yes, so an expert should review."),
    )
    for field_id, value, message in triggers:
        if answers.get(field_id) == value:
            flags.append(
                Flag(
                    code=f"expert_{field_id}",
                    fields=[field_id],
                    message=message,
                    severity="info",
                    needs_expert=True,
                )
            )
    return flags


def _rule_low_ai_confidence(
    ai_suggestions: dict[str, Any],
    field_sources: dict[str, str],
    answers: dict[str, Any],
) -> list[Flag]:
    flags: list[Flag] = []
    for field_id, raw in ai_suggestions.items():
        if not isinstance(raw, dict):
            continue
        conf = _ai_confidence(ai_suggestions, field_id)
        if conf is None or conf >= AI_LOW_CONFIDENCE:
            continue
        source = field_sources.get(field_id)
        # Flag when the citizen kept an AI-backed answer, or answered the same value.
        if source in {"ai_accepted", "ai_edited"} or (
            field_id in answers and answers.get(field_id) == raw.get("value")
        ):
            flags.append(
                Flag(
                    code="low_ai_confidence",
                    fields=[field_id],
                    message=(
                        f"The AI confidence for '{field_id}' is below {AI_LOW_CONFIDENCE}. "
                        "Please double-check this answer."
                    ),
                    severity="warning",
                    needs_expert=False,
                )
            )
    return flags


def _rule_unusable_photos(unusable_photos: list[str]) -> list[Flag]:
    if not unusable_photos:
        return []
    roles = ", ".join(unusable_photos)
    return [
        Flag(
            code="unusable_photo",
            fields=[f"photo_{role}" for role in unusable_photos],
            message=f"One or more photos look unusable ({roles}). Please retake if you can.",
            severity="warning",
            needs_expert=False,
        )
    ]


def _rule_gps_distance(
    *,
    site_lat: float | None,
    site_lon: float | None,
    user_lat: float | None,
    user_lon: float | None,
    max_m: float,
) -> list[Flag]:
    if None in (site_lat, site_lon, user_lat, user_lon):
        return []
    distance = haversine_m(user_lat, user_lon, site_lat, site_lon)  # type: ignore[arg-type]
    if distance > max_m:
        return [
            Flag(
                code="gps_far_from_site",
                fields=["site"],
                message=(
                    f"Your location is about {distance:.0f} m from the chosen site "
                    f"(threshold {max_m:g} m). Confirm you picked the right site."
                ),
                severity="warning",
                needs_expert=False,
            )
        ]
    return []


def _rule_overall_mismatch(answers: dict[str, Any]) -> list[Flag]:
    user = answers.get("overall_assessment")
    if user not in OVERALL_LEVELS:
        return []
    suggested, _count = suggest_overall_from_answers(answers)
    delta = abs(level_index(str(user)) - level_index(suggested))
    if delta >= 2:
        return [
            Flag(
                code="overall_mismatch",
                fields=["overall_assessment"],
                message=(
                    f"Your overall rating ({user}) differs by two levels from the "
                    f"advisory rating ({suggested}) based on pressure signals. "
                    "This record will be reviewed."
                ),
                severity="warning",
                needs_expert=True,
            )
        ]
    return []
