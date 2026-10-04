"""Table-driven tests for risk notes and overall advisory rating."""

from __future__ import annotations

import pytest

from app.risk import (
    DISCLAIMER,
    RAINFALL_CONTACT_HIGH_MM,
    build_risk_bundle,
    contact_safety_note,
    count_pressure_signals,
    ecosystem_pressure_note,
    overall_mismatch_levels,
    suggest_overall_from_answers,
    suggest_overall_from_count,
)

PRESSURE_CASES = [
    ("empty_good", {}, "good", 0),
    (
        "two_signals_good",
        {"bottom_type": "B", "bank_type": "B"},
        "good",
        2,
    ),
    (
        "three_signals_moderate",
        {"bottom_type": "B", "bank_type": "B", "impervious_left": "yes"},
        "moderate",
        3,
    ),
    (
        "six_signals_poor",
        {
            "bottom_type": "B",
            "bank_type": "B",
            "impervious_left": "yes",
            "impervious_right": "yes",
            "vegetation_left": "no",
            "vegetation_right": "no",
        },
        "poor",
        6,
    ),
]


@pytest.mark.parametrize(
    "case_id,answers,expected_overall,expected_count",
    PRESSURE_CASES,
    ids=[c[0] for c in PRESSURE_CASES],
)
def test_pressure_bands(case_id, answers, expected_overall, expected_count):
    count, _ = count_pressure_signals(answers)
    assert count == expected_count
    assert suggest_overall_from_count(count) == expected_overall
    suggested, c2 = suggest_overall_from_answers(answers)
    assert suggested == expected_overall
    assert c2 == expected_count


CONTACT_CASES = [
    ("sewage_high", {"sewage_discharge": "yes"}, None, "high"),
    ("pipes_high", {"draining_pipes": "yes"}, None, "high"),
    ("foam_high", {"water_aspect": "C"}, None, "high"),
    ("colour_high", {"water_aspect": "D"}, None, "high"),
    (
        "turbid_with_rain_high",
        {"water_aspect": "B"},
        RAINFALL_CONTACT_HIGH_MM,
        "high",
    ),
    (
        "turbid_without_rain_moderate",
        {"water_aspect": "B"},
        2.0,
        "moderate",
    ),
    ("stagnant_moderate", {"water_flow": "C"}, None, "moderate"),
    ("clear_low", {"water_aspect": "A", "water_flow": "A"}, None, "low"),
]


@pytest.mark.parametrize(
    "case_id,answers,rainfall,expected",
    CONTACT_CASES,
    ids=[c[0] for c in CONTACT_CASES],
)
def test_contact_safety(case_id, answers, rainfall, expected):
    note = contact_safety_note(answers, rainfall_48h_mm=rainfall)
    assert note.level == expected
    assert note.reasons


ECOSYSTEM_CASES = [
    ("none_low", {}, "low"),
    ("one_moderate", {"barriers": "yes"}, "moderate"),
    (
        "three_high",
        {"bottom_type": "B", "bank_type": "B", "construction": "yes"},
        "high",
    ),
]


@pytest.mark.parametrize(
    "case_id,answers,expected",
    ECOSYSTEM_CASES,
    ids=[c[0] for c in ECOSYSTEM_CASES],
)
def test_ecosystem_pressure(case_id, answers, expected):
    note = ecosystem_pressure_note(answers)
    assert note.level == expected


def test_disclaimer_always_present():
    bundle = build_risk_bundle({"water_aspect": "A"})
    assert bundle.disclaimer == DISCLAIMER
    assert DISCLAIMER.startswith("Indicative only")


def test_overall_mismatch_levels():
    assert overall_mismatch_levels("good", "poor") == 2
    assert overall_mismatch_levels("good", "moderate") == 1
    assert overall_mismatch_levels("moderate", "moderate") == 0
    assert overall_mismatch_levels(None, "good") is None


def test_count_bands_boundaries():
    assert suggest_overall_from_count(0) == "good"
    assert suggest_overall_from_count(2) == "good"
    assert suggest_overall_from_count(3) == "moderate"
    assert suggest_overall_from_count(5) == "moderate"
    assert suggest_overall_from_count(6) == "poor"
