"""Merge upstream and downstream suggestions."""

from __future__ import annotations

from app.ai.models import FieldSuggestion, RoleAnalysisResult
from app.ai.prompts import ROLE_FIELDS

YES_WINS_FIELDS = frozenset({"draining_pipes", "sewage_discharge", "construction"})
STREAM_FIELDS = ROLE_FIELDS["upstream"]


def merge_stream_pair(
    upstream: RoleAnalysisResult | None,
    downstream: RoleAnalysisResult | None,
) -> tuple[dict[str, FieldSuggestion], str | None, list[str]]:
    """Merge Group A results.

    Returns (suggestions, upstream_vs_downstream_note, needs_expert_hints).
    """
    if upstream is None and downstream is None:
        return {}, None, []
    if upstream is None:
        assert downstream is not None
        return dict(downstream.suggestions), downstream.note, _expert_hints(downstream.suggestions)
    if downstream is None:
        return dict(upstream.suggestions), upstream.note, _expert_hints(upstream.suggestions)

    merged: dict[str, FieldSuggestion] = {}
    needs_expert: list[str] = []
    differ_fields: list[str] = []

    for field_id in STREAM_FIELDS:
        left = upstream.suggestions.get(field_id)
        right = downstream.suggestions.get(field_id)
        if left is None and right is None:
            continue
        if left is None:
            assert right is not None
            merged[field_id] = right
            continue
        if right is None:
            merged[field_id] = left
            continue

        if field_id in YES_WINS_FIELDS:
            chosen = _yes_wins(left, right)
            merged[field_id] = chosen
            if chosen.value == "yes":
                needs_expert.append(field_id)
            elif left.value != right.value:
                differ_fields.append(field_id)
            continue

        if left.value == right.value:
            # Agree → keep value with the lower confidence.
            chosen = left if left.confidence <= right.confidence else right
            merged[field_id] = FieldSuggestion(
                value=chosen.value,
                confidence=chosen.confidence,
                reason=chosen.reason,
            )
        else:
            differ_fields.append(field_id)
            merged[field_id] = FieldSuggestion(
                value="not_sure",
                confidence=0.0,
                reason="upstream and downstream photos differ",
            )

    note = _build_note(upstream, downstream, differ_fields)
    # Also catch yes from single-side already covered; ensure unique.
    for field_id in YES_WINS_FIELDS:
        suggestion = merged.get(field_id)
        if suggestion and suggestion.value == "yes" and field_id not in needs_expert:
            needs_expert.append(field_id)

    return merged, note, needs_expert


def _yes_wins(left: FieldSuggestion, right: FieldSuggestion) -> FieldSuggestion:
    if left.value == "yes" and right.value != "yes":
        return left
    if right.value == "yes" and left.value != "yes":
        return right
    if left.value == right.value:
        return left if left.confidence <= right.confidence else right
    # neither yes, values differ → not_sure
    return FieldSuggestion(
        value="not_sure",
        confidence=0.0,
        reason="upstream and downstream photos differ",
    )


def _expert_hints(suggestions: dict[str, FieldSuggestion]) -> list[str]:
    return [
        field_id
        for field_id in YES_WINS_FIELDS
        if suggestions.get(field_id) and suggestions[field_id].value == "yes"
    ]


def _build_note(
    upstream: RoleAnalysisResult,
    downstream: RoleAnalysisResult,
    differ_fields: list[str],
) -> str | None:
    for candidate in (upstream.note, downstream.note):
        if candidate:
            return candidate
    up_aspect = upstream.suggestions.get("water_aspect")
    down_aspect = downstream.suggestions.get("water_aspect")
    if (
        up_aspect
        and down_aspect
        and up_aspect.value != down_aspect.value
        and "not_sure" not in {up_aspect.value, down_aspect.value}
    ):
        return (
            f"Upstream water looks like '{up_aspect.value}' while downstream looks like "
            f"'{down_aspect.value}'."
        )
    if differ_fields:
        return "Upstream and downstream photos differ on: " + ", ".join(differ_fields) + "."
    return None
