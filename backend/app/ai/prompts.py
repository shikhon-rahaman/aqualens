"""System prompts and per-role field lists (docs/02 section 3)."""

from __future__ import annotations

ROLE_FIELDS: dict[str, list[str]] = {
    "upstream": [
        "water_aspect",
        "water_flow",
        "bottom_type",
        "bank_type",
        "channel_form",
        "barriers",
        "draining_pipes",
        "sewage_discharge",
        "water_withdrawal",
        "habitats_present",
        "natural_debris_present",
    ],
    "downstream": [
        "water_aspect",
        "water_flow",
        "bottom_type",
        "bank_type",
        "channel_form",
        "barriers",
        "draining_pipes",
        "sewage_discharge",
        "water_withdrawal",
        "habitats_present",
        "natural_debris_present",
    ],
    "context": [
        "impervious_left",
        "impervious_right",
        "vegetation_left",
        "vegetation_right",
        "veg_type_left",
        "veg_type_right",
        "construction",
    ],
    "biodiversity": [
        "possible_taxon_group",
    ],
}

SYSTEM_PROMPT = """You help citizens assess urban streams from ONE photo.
Rules:
- Answer only what is clearly visible. If unsure, use "not_sure". Never guess.
- Each field must be {"value": "...", "confidence": 0.0 to 1.0, "reason": "one short sentence about what is visible"}.
- For water_flow, ONLY return a confidence above 0.5 if the value is D (dry) and dry ground is clearly visible. For A, B, or C, ALWAYS return confidence 0.3 or below, since motion cannot be judged from a still photo.
- Never set confidence above 0.6 for channel_form from a still photo.
- For draining_pipes, sewage_discharge, construction: describe only what is visible. Never accuse a person or company. Never state a cause.
- For margin fields (impervious_*, vegetation_*, veg_type_*): report left/right as seen in the image, not stream-left/right.
- No safety advice. For possible invasive or biodiversity cues, stay uncertain; use candidates only.
- Output JSON only. No markdown fences, no extra text.
"""


def user_prompt_for_role(role: str) -> str:
    fields = ROLE_FIELDS[role]
    lines = [
        f"Photo role: {role}.",
        "Return a JSON object with exactly these keys:",
    ]
    for field_id in fields:
        lines.append(f"- {field_id}")
    if role in {"upstream", "downstream"}:
        lines.append(
            '- optional "upstream_vs_downstream": one sentence if clarity/colour differs within this view'
        )
    if role == "biodiversity":
        lines.append(
            'possible_taxon_group value must be one of: plant, animal, fungus, other, unsure'
        )
    lines.append(
        'Also include "image_quality": {"usable": true|false, "issue": ""}.'
    )
    lines.append("Use letter codes A/B/C/D or yes/no/not_sure as required by each field.")
    return "\n".join(lines)


def fields_for_role(role: str) -> list[str]:
    if role not in ROLE_FIELDS:
        raise ValueError(f"unknown photo role: {role}")
    return list(ROLE_FIELDS[role])
