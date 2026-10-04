"""Rule-based risk notes and advisory overall rating.

Indicative only — never a safety certification. Thresholds are constants.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["low", "moderate", "high"]
OverallLevel = Literal["good", "moderate", "poor"]

DISCLAIMER = "Indicative only, not a safety certification"
OVERALL_LEVELS: tuple[OverallLevel, ...] = ("good", "moderate", "poor")

# Contact-safety: rainfall (mm in last 48h) that elevates turbid water to High.
RAINFALL_CONTACT_HIGH_MM = 10.0
# Ecosystem High when this many ecosystem pressure signals are present.
ECOSYSTEM_HIGH_MIN_SIGNALS = 3
ECOSYSTEM_MODERATE_MIN_SIGNALS = 1


class RiskNote(BaseModel):
    level: RiskLevel
    reasons: list[str] = Field(default_factory=list)


class RiskBundle(BaseModel):
    contact: RiskNote
    ecosystem: RiskNote
    disclaimer: str = DISCLAIMER


def level_index(level: str) -> int:
    try:
        return OVERALL_LEVELS.index(level)  # type: ignore[arg-type]
    except ValueError:
        return -1


def count_pressure_signals(answers: dict[str, Any]) -> tuple[int, list[str]]:
    """Count docs/02 §4.10 pressure signals. Each matching condition adds one."""
    reasons: list[str] = []

    def add(condition: bool, reason: str) -> None:
        if condition:
            reasons.append(reason)

    add(answers.get("bottom_type") == "B", "Artificial channel bed")
    add(answers.get("bank_type") == "B", "Artificial channel banks")
    add(answers.get("impervious_left") == "yes", "Impervious cover on image-left margin")
    add(answers.get("impervious_right") == "yes", "Impervious cover on image-right margin")
    add(answers.get("vegetation_left") == "no", "Missing vegetation on image-left margin")
    add(answers.get("vegetation_right") == "no", "Missing vegetation on image-right margin")
    add(
        answers.get("water_aspect") in {"B", "C", "D"},
        "Non-clear water (turbid, foam, or altered colour)",
    )
    add(answers.get("draining_pipes") == "yes", "Draining pipe marked yes")
    add(answers.get("sewage_discharge") == "yes", "Sewage discharge marked yes")
    add(answers.get("barriers") == "yes", "Barrier or dam marked yes")
    add(answers.get("construction") == "yes", "Construction in stream marked yes")
    add(answers.get("water_withdrawal") == "yes", "Water withdrawal marked yes")
    add(answers.get("vegetation_cuts") == "yes", "Recent vegetation cuts marked yes")

    return len(reasons), reasons


def suggest_overall_from_count(pressure_count: int) -> OverallLevel:
    if pressure_count <= 2:
        return "good"
    if pressure_count <= 5:
        return "moderate"
    return "poor"


def suggest_overall_from_answers(answers: dict[str, Any]) -> tuple[OverallLevel, int]:
    count, _ = count_pressure_signals(answers)
    return suggest_overall_from_count(count), count


def overall_mismatch_levels(user: str | None, suggested: OverallLevel) -> int | None:
    if user not in OVERALL_LEVELS:
        return None
    return abs(level_index(user) - level_index(suggested))


def contact_safety_note(
    answers: dict[str, Any],
    *,
    rainfall_48h_mm: float | None = None,
    rainfall_high_mm: float = RAINFALL_CONTACT_HIGH_MM,
) -> RiskNote:
    reasons: list[str] = []
    high = False
    moderate = False

    aspect = answers.get("water_aspect")
    flow = answers.get("water_flow")

    if answers.get("sewage_discharge") == "yes":
        high = True
        reasons.append("Sewage discharge marked yes")
    if answers.get("draining_pipes") == "yes":
        high = True
        reasons.append("Draining pipe marked yes")
    if aspect in {"C", "D"}:
        high = True
        reasons.append("Water shows foam or altered colour")
    if aspect == "B":
        if rainfall_48h_mm is not None and rainfall_48h_mm >= rainfall_high_mm:
            high = True
            reasons.append(
                f"Turbid water with recent rainfall "
                f"({rainfall_48h_mm:.1f} mm in 48 h ≥ {rainfall_high_mm:g} mm)"
            )
        else:
            moderate = True
            reasons.append("Water looks muddy or turbid")

    if flow == "C":
        moderate = True
        reasons.append("Flow is stagnant or intermittent")
    if flow == "D":
        # Dry bed: lower contact concern from water itself, but note it.
        reasons.append("Channel marked dry — little standing water for contact")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_reasons = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            unique_reasons.append(reason)

    if high:
        return RiskNote(level="high", reasons=unique_reasons)
    if moderate:
        return RiskNote(level="moderate", reasons=unique_reasons or ["Some water conditions need care"])
    if unique_reasons:
        return RiskNote(level="low", reasons=unique_reasons)
    return RiskNote(level="low", reasons=["No elevated contact-safety signals from the answers"])


def ecosystem_pressure_note(
    answers: dict[str, Any],
    *,
    high_min: int = ECOSYSTEM_HIGH_MIN_SIGNALS,
    moderate_min: int = ECOSYSTEM_MODERATE_MIN_SIGNALS,
) -> RiskNote:
    signals: list[str] = []

    def add(condition: bool, reason: str) -> None:
        if condition:
            signals.append(reason)

    add(answers.get("bottom_type") == "B", "Artificial channel bed")
    add(answers.get("bank_type") == "B", "Artificial channel banks")
    add(answers.get("impervious_left") == "yes", "Impervious image-left margin")
    add(answers.get("impervious_right") == "yes", "Impervious image-right margin")
    add(answers.get("vegetation_left") == "no", "Missing vegetation image-left")
    add(answers.get("vegetation_right") == "no", "Missing vegetation image-right")
    add(answers.get("barriers") == "yes", "Barrier present")
    add(answers.get("construction") == "yes", "Construction in stream")
    add(answers.get("vegetation_cuts") == "yes", "Recent vegetation cuts")

    count = len(signals)
    if count >= high_min:
        return RiskNote(level="high", reasons=signals)
    if count >= moderate_min:
        return RiskNote(level="moderate", reasons=signals)
    return RiskNote(
        level="low",
        reasons=signals or ["Few ecosystem-pressure signals from the answers"],
    )


def build_risk_bundle(
    answers: dict[str, Any],
    *,
    rainfall_48h_mm: float | None = None,
) -> RiskBundle:
    return RiskBundle(
        contact=contact_safety_note(answers, rainfall_48h_mm=rainfall_48h_mm),
        ecosystem=ecosystem_pressure_note(answers),
        disclaimer=DISCLAIMER,
    )
