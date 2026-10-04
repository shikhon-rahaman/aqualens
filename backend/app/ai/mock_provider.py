"""Deterministic mock vision provider (no network)."""

from __future__ import annotations

import hashlib

from app.ai.models import FieldSuggestion, RoleAnalysisResult, normalize_suggestion
from app.ai.prompts import fields_for_role

# Stable defaults per field for demos and offline UI.
_DEFAULTS: dict[str, tuple[str, float, str]] = {
    "water_aspect": ("A", 0.72, "Mock: water surface looks clear."),
    "water_flow": ("B", 0.45, "Mock: slow movement suggested by surface texture."),
    "bottom_type": ("A", 0.55, "Mock: bed looks natural."),
    "bank_type": ("A", 0.55, "Mock: banks look natural."),
    "channel_form": ("B", 0.4, "Mock: channel appears U-shaped."),
    "barriers": ("no", 0.5, "Mock: no barrier visible."),
    "draining_pipes": ("no", 0.5, "Mock: no pipe visible."),
    "sewage_discharge": ("no", 0.5, "Mock: no discharge visible."),
    "water_withdrawal": ("no", 0.5, "Mock: no withdrawal visible."),
    "habitats_present": ("not_sure", 0.3, "Mock: habitats unclear."),
    "natural_debris_present": ("not_sure", 0.3, "Mock: debris unclear."),
    "impervious_left": ("no", 0.5, "Mock: left margin not clearly paved."),
    "impervious_right": ("no", 0.5, "Mock: right margin not clearly paved."),
    "vegetation_left": ("yes", 0.55, "Mock: vegetation visible on image-left."),
    "vegetation_right": ("yes", 0.55, "Mock: vegetation visible on image-right."),
    "veg_type_left": ("A", 0.45, "Mock: herbs dominate image-left."),
    "veg_type_right": ("A", 0.45, "Mock: herbs dominate image-right."),
    "construction": ("no", 0.5, "Mock: no construction visible."),
    "possible_taxon_group": ("plant", 0.4, "Mock: possible plant feature."),
}


class MockProvider:
    name = "mock"

    def __init__(self, overrides: dict[str, dict[str, FieldSuggestion]] | None = None) -> None:
        # role → field_id → suggestion, for tests
        self.overrides = overrides or {}

    def analyze(self, image_bytes: bytes, role: str) -> RoleAnalysisResult:
        fields = fields_for_role(role)
        digest = hashlib.sha256(image_bytes).hexdigest()
        # Tiny deterministic nudge from image hash so identical images stay stable.
        nudge = (int(digest[:2], 16) % 5) / 100.0

        suggestions: dict[str, FieldSuggestion] = {}
        role_overrides = self.overrides.get(role, {})
        for field_id in fields:
            if field_id in role_overrides:
                suggestions[field_id] = role_overrides[field_id]
                continue
            value, confidence, reason = _DEFAULTS.get(
                field_id, ("not_sure", 0.2, "Mock: not enough detail.")
            )
            suggestions[field_id] = normalize_suggestion(
                field_id,
                {
                    "value": value,
                    "confidence": min(1.0, confidence + nudge),
                    "reason": reason,
                },
            )

        return RoleAnalysisResult(
            role=role,
            suggestions=suggestions,
            note=None,
            image_usable=True,
        )
