"""Table-driven tests for docs/02 §4 validation rules."""

from __future__ import annotations

import pytest

from app.validation import (
    AI_ASPECT_CONFLICT_CONFIDENCE,
    AI_LOW_CONFIDENCE,
    GPS_FLAG_DISTANCE_M,
    Flag,
    validate_answers_rules,
)

# Site near Bangalore-ish for distance tests
SITE = {"site_lat": 12.9700, "site_lon": 77.5900}


def _codes(flags: list[Flag]) -> list[str]:
    return [f.code for f in flags]


def _has(flags: list[Flag], code: str) -> bool:
    return any(f.code == code for f in flags)


# Each row: id, answers, kwargs extras, expected code present?, expected code
CASES = [
    # 1 dry vs height
    (
        "dry_height_conflict",
        {"water_flow": "D", "water_height": 12},
        {},
        True,
        "dry_vs_height",
    ),
    (
        "dry_height_zero_ok",
        {"water_flow": "D", "water_height": 0},
        {},
        False,
        "dry_vs_height",
    ),
    (
        "flow_wet_with_height_ok",
        {"water_flow": "B", "water_height": 12},
        {},
        False,
        "dry_vs_height",
    ),
    # 2 sewage without pipes
    (
        "sewage_yes_pipes_no",
        {"sewage_discharge": "yes", "draining_pipes": "no"},
        {},
        True,
        "sewage_without_pipes",
    ),
    (
        "sewage_yes_pipes_yes_ok",
        {"sewage_discharge": "yes", "draining_pipes": "yes"},
        {},
        False,
        "sewage_without_pipes",
    ),
    # 3 clear vs AI turbid
    (
        "clear_vs_ai_turbid",
        {"water_aspect": "A"},
        {
            "ai_suggestions": {
                "water_aspect": {
                    "value": "B",
                    "confidence": AI_ASPECT_CONFLICT_CONFIDENCE,
                    "reason": "muddy",
                }
            }
        },
        True,
        "clear_vs_ai_turbid",
    ),
    (
        "clear_vs_ai_low_conf_ok",
        {"water_aspect": "A"},
        {
            "ai_suggestions": {
                "water_aspect": {"value": "B", "confidence": 0.4, "reason": "maybe muddy"}
            }
        },
        False,
        "clear_vs_ai_turbid",
    ),
    (
        "user_already_turbid_ok",
        {"water_aspect": "B"},
        {
            "ai_suggestions": {
                "water_aspect": {"value": "B", "confidence": 0.9, "reason": "muddy"}
            }
        },
        False,
        "clear_vs_ai_turbid",
    ),
    # 4 water height range
    (
        "height_too_high",
        {"water_height": 301},
        {},
        True,
        "water_height_out_of_range",
    ),
    (
        "height_negative",
        {"water_height": -1},
        {},
        True,
        "water_height_out_of_range",
    ),
    (
        "height_in_range_ok",
        {"water_height": 40},
        {},
        False,
        "water_height_out_of_range",
    ),
    # 5 veg type without presence
    (
        "veg_type_left_without_yes",
        {"vegetation_left": "no", "veg_type_left": "A"},
        {},
        True,
        "veg_type_without_presence_left",
    ),
    (
        "veg_type_right_without_yes",
        {"vegetation_right": "no", "veg_type_right": "B"},
        {},
        True,
        "veg_type_without_presence_right",
    ),
    (
        "veg_type_with_yes_ok",
        {"vegetation_left": "yes", "veg_type_left": "A"},
        {},
        False,
        "veg_type_without_presence_left",
    ),
    # 6 AI trees vs no veg
    (
        "ai_trees_vs_no_veg_left",
        {"vegetation_left": "no"},
        {
            "ai_suggestions": {
                "veg_type_left": {
                    "value": "C",
                    "confidence": 0.8,
                    "reason": "trees visible",
                }
            }
        },
        True,
        "ai_trees_vs_no_veg_left",
    ),
    (
        "ai_herbs_vs_no_veg_ok",
        {"vegetation_left": "no"},
        {
            "ai_suggestions": {
                "veg_type_left": {"value": "A", "confidence": 0.8, "reason": "herbs"}
            }
        },
        False,
        "ai_trees_vs_no_veg_left",
    ),
    # 7 expert triggers
    (
        "expert_pipes",
        {"draining_pipes": "yes"},
        {},
        True,
        "expert_draining_pipes",
    ),
    (
        "expert_sewage",
        {"sewage_discharge": "yes"},
        {},
        True,
        "expert_sewage_discharge",
    ),
    (
        "expert_construction",
        {"construction": "yes"},
        {},
        True,
        "expert_construction",
    ),
    (
        "expert_cuts",
        {"vegetation_cuts": "yes"},
        {},
        True,
        "expert_vegetation_cuts",
    ),
    (
        "expert_invasive",
        {"invasive_species": "yes"},
        {},
        True,
        "expert_invasive_species",
    ),
    (
        "expert_no_when_no",
        {"draining_pipes": "no", "construction": "no"},
        {},
        False,
        "expert_draining_pipes",
    ),
    # 8 low AI confidence / unusable
    (
        "low_ai_confidence_accepted",
        {"water_aspect": "A"},
        {
            "ai_suggestions": {
                "water_aspect": {
                    "value": "A",
                    "confidence": AI_LOW_CONFIDENCE - 0.1,
                    "reason": "uncertain",
                }
            },
            "field_sources": {"water_aspect": "ai_accepted"},
        },
        True,
        "low_ai_confidence",
    ),
    (
        "high_ai_confidence_ok",
        {"water_aspect": "A"},
        {
            "ai_suggestions": {
                "water_aspect": {"value": "A", "confidence": 0.8, "reason": "clear"}
            },
            "field_sources": {"water_aspect": "ai_accepted"},
        },
        False,
        "low_ai_confidence",
    ),
    (
        "unusable_photo",
        {},
        {"unusable_photos": ["upstream"]},
        True,
        "unusable_photo",
    ),
    # 9 GPS distance
    (
        "gps_far",
        {},
        {
            **SITE,
            "user_lat": 12.9800,
            "user_lon": 77.6000,  # ~1.5 km
        },
        True,
        "gps_far_from_site",
    ),
    (
        "gps_near_ok",
        {},
        {
            **SITE,
            "user_lat": 12.9705,
            "user_lon": 77.5905,  # ~70 m
        },
        False,
        "gps_far_from_site",
    ),
    (
        "gps_missing_ok",
        {},
        {**SITE, "user_lat": None, "user_lon": None},
        False,
        "gps_far_from_site",
    ),
    # 10 overall mismatch (good vs poor = 2 levels)
    (
        "overall_two_level_mismatch",
        {
            "overall_assessment": "good",
            "bottom_type": "B",
            "bank_type": "B",
            "impervious_left": "yes",
            "impervious_right": "yes",
            "vegetation_left": "no",
            "vegetation_right": "no",
            "water_aspect": "D",
            "draining_pipes": "yes",
            "barriers": "yes",
        },
        {},
        True,
        "overall_mismatch",
    ),
    (
        "overall_match_ok",
        {
            "overall_assessment": "good",
            "bottom_type": "A",
            "bank_type": "A",
            "water_aspect": "A",
        },
        {},
        False,
        "overall_mismatch",
    ),
]


@pytest.mark.parametrize(
    "case_id,answers,extras,expect_present,code",
    CASES,
    ids=[c[0] for c in CASES],
)
def test_validation_table(case_id, answers, extras, expect_present, code):
    flags = validate_answers_rules(answers, **extras)
    present = _has(flags, code)
    assert present is expect_present, f"{case_id}: codes={_codes(flags)}"


def test_expert_flags_set_needs_expert():
    flags = validate_answers_rules({"draining_pipes": "yes"})
    expert = [f for f in flags if f.code == "expert_draining_pipes"]
    assert expert and expert[0].needs_expert is True


def test_gps_threshold_constant():
    assert GPS_FLAG_DISTANCE_M == 500.0


def test_overall_mismatch_needs_expert():
    answers = {
        "overall_assessment": "good",
        "bottom_type": "B",
        "bank_type": "B",
        "impervious_left": "yes",
        "impervious_right": "yes",
        "vegetation_left": "no",
        "vegetation_right": "no",
        "water_aspect": "C",
        "sewage_discharge": "yes",
        "construction": "yes",
    }
    flags = validate_answers_rules(answers)
    mismatch = next(f for f in flags if f.code == "overall_mismatch")
    assert mismatch.needs_expert is True
