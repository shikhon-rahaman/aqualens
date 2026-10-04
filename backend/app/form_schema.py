"""Single source of truth for assessment form fields.

Plain-language questions and help are original AquaLens wording — not copied
from the official OneAquaHealth app. PENDING habitat/debris letter codes and
water-height unit stay presence-only / soft-labelled until confirmed.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AiRole = Literal["suggest", "human_only", "candidates_only", "none"]
ValueType = Literal["choice", "number", "feelings", "text", "site", "media"]
FieldSource = Literal["ai_accepted", "ai_edited", "human", "unanswered"]

FIELD_SOURCES: frozenset[str] = frozenset(
    {"ai_accepted", "ai_edited", "human", "unanswered"}
)

WATER_HEIGHT_SOFT_MIN = 0.0
WATER_HEIGHT_SOFT_MAX = 300.0
FEELINGS_KEYS = ("joy", "serenity", "anger", "fear")
PHOTO_ROLES = ("upstream", "downstream", "context", "biodiversity")


class FieldDef(BaseModel):
    id: str
    group: str
    question: str
    help: str
    ai_role: AiRole
    value_type: ValueType
    values: list[str] | None = None
    value_labels: dict[str, str] | None = None
    pending: bool = False
    pending_note: str | None = None


YES_NO = ["yes", "no", "not_sure"]
YES_NO_LABELS = {"yes": "Yes", "no": "No", "not_sure": "Not sure"}


def _yn(
    field_id: str,
    group: str,
    question: str,
    help_text: str,
    ai_role: AiRole,
    *,
    pending: bool = False,
    pending_note: str | None = None,
) -> FieldDef:
    return FieldDef(
        id=field_id,
        group=group,
        question=question,
        help=help_text,
        ai_role=ai_role,
        value_type="choice",
        values=list(YES_NO),
        value_labels=dict(YES_NO_LABELS),
        pending=pending,
        pending_note=pending_note,
    )


FIELDS: list[FieldDef] = [
    FieldDef(
        id="site",
        group="site",
        question="Which research site is this?",
        help="Pick the nearest listed demo site, or add a new informal site if none fit.",
        ai_role="suggest",
        value_type="site",
    ),
    FieldDef(
        id="photo_upstream",
        group="media",
        question="Upstream photo",
        help="Photo looking upstream along the channel.",
        ai_role="none",
        value_type="media",
    ),
    FieldDef(
        id="photo_downstream",
        group="media",
        question="Downstream photo",
        help="Photo looking downstream along the channel.",
        ai_role="none",
        value_type="media",
    ),
    FieldDef(
        id="photo_context",
        group="media",
        question="Surrounding context photo",
        help="Show nearby roads, buildings, or land use around the stream.",
        ai_role="none",
        value_type="media",
    ),
    FieldDef(
        id="photo_biodiversity",
        group="media",
        question="Biodiversity photo",
        help="Optional close-up of a plant, animal, or other living feature of interest.",
        ai_role="none",
        value_type="media",
    ),
    FieldDef(
        id="channel_form",
        group="questions_1",
        question="What shape is the channel?",
        help="Look at the cross-section: flat, U-shaped, or V-shaped. Choose Not sure if unclear.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "C", "not_sure"],
        value_labels={
            "A": "Flat",
            "B": "U shape",
            "C": "V shape",
            "not_sure": "Not sure",
        },
    ),
    FieldDef(
        id="bottom_type",
        group="questions_1",
        question="What is the wet channel bottom made of?",
        help="Natural sediment versus concrete or stones set in concrete.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "not_sure"],
        value_labels={
            "A": "Natural",
            "B": "Artificial (concrete / stones with concrete)",
            "not_sure": "Not sure",
        },
    ),
    FieldDef(
        id="bank_type",
        group="questions_1",
        question="What are the channel banks like?",
        help="Natural earth or vegetation, hard artificial walls, or loose laid stones.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "C", "not_sure"],
        value_labels={
            "A": "Natural",
            "B": "Artificial",
            "C": "Laid stones without concrete",
            "not_sure": "Not sure",
        },
    ),
    _yn(
        "habitats_present",
        "questions_1",
        "Are any in-stream habitats visible?",
        "Presence only for now. Habitat letter codes (A–E) are not confirmed yet.",
        "suggest",
        pending=True,
        pending_note="Types A–E unknown; presence-only until confirmed in the official app.",
    ),
    _yn(
        "natural_debris_present",
        "questions_1",
        "Is natural debris visible in or beside the stream?",
        "Presence only for now. Debris letter codes (A–C) are not confirmed yet.",
        "suggest",
        pending=True,
        pending_note="Types A–C unknown; presence-only until confirmed in the official app.",
    ),
    FieldDef(
        id="water_flow",
        group="questions_1",
        question="How is the water flowing?",
        help="Judge speed and continuity as best you can from still photos and what you see on site.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "C", "D", "not_sure"],
        value_labels={
            "A": "Fast",
            "B": "Slow",
            "C": "Stagnant or intermittent",
            "D": "Dry",
            "not_sure": "Not sure",
        },
    ),
    FieldDef(
        id="water_aspect",
        group="questions_2",
        question="How does the water look?",
        help="Describe clarity and surface appearance: clear, muddy, foamy, or oddly coloured.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "C", "D", "not_sure"],
        value_labels={
            "A": "Clear",
            "B": "Muddy / turbid",
            "C": "Foam",
            "D": "Colours / altered colour",
            "not_sure": "Not sure",
        },
    ),
    _yn(
        "water_withdrawal",
        "questions_2",
        "Is there obvious water collection, use, or removal?",
        "Only mark yes when collection equipment or active removal is clearly visible.",
        "suggest",
    ),
    _yn(
        "barriers",
        "questions_2",
        "Are there dams or other barriers across the stream?",
        "Look for walls, weirs, or other structures that block or cross the channel.",
        "suggest",
    ),
    _yn(
        "draining_pipes",
        "questions_2",
        "Are pipes visible that appear to drain into the stream?",
        "Describe only what you see. A yes answer will be queued for expert review.",
        "suggest",
    ),
    _yn(
        "sewage_discharge",
        "questions_2",
        "Is there any visible water entry that may be sewage or wastewater?",
        "Mark yes only when an entry or discharge is visible. Experts will review yes answers.",
        "suggest",
    ),
    _yn(
        "construction",
        "questions_2",
        "Is construction or works happening in the stream?",
        "Machinery, fresh works, or active building in the channel count as yes.",
        "suggest",
    ),
    FieldDef(
        id="water_height",
        group="questions_2",
        question="What is the water height?",
        help="Enter a number in cm (unit to be confirmed). Leave blank if you could not measure.",
        ai_role="human_only",
        value_type="number",
        pending=True,
        pending_note="Unit unconfirmed; label as cm (to be confirmed). Soft range 0–300.",
    ),
    _yn(
        "impervious_left",
        "questions_3",
        "Is more than one third of the left margin covered by roads, sidewalks, or buildings?",
        "Left and right are defined looking downstream.",
        "suggest",
    ),
    _yn(
        "impervious_right",
        "questions_3",
        "Is more than one third of the right margin covered by roads, sidewalks, or buildings?",
        "Left and right are defined looking downstream.",
        "suggest",
    ),
    _yn(
        "vegetation_left",
        "questions_3",
        "Is the left margin covered by vegetation?",
        "If no, skip the vegetation type for that side.",
        "suggest",
    ),
    _yn(
        "vegetation_right",
        "questions_3",
        "Is the right margin covered by vegetation?",
        "If no, skip the vegetation type for that side.",
        "suggest",
    ),
    FieldDef(
        id="veg_type_left",
        group="questions_3",
        question="What is the dominant vegetation on the left margin?",
        help="Choose the type that covers more than half of the first five metres from the bank top.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "C", "not_sure"],
        value_labels={
            "A": "Herbs",
            "B": "Shrubs",
            "C": "Trees",
            "not_sure": "Not sure",
        },
    ),
    FieldDef(
        id="veg_type_right",
        group="questions_3",
        question="What is the dominant vegetation on the right margin?",
        help="Choose the type that covers more than half of the first five metres from the bank top.",
        ai_role="suggest",
        value_type="choice",
        values=["A", "B", "C", "not_sure"],
        value_labels={
            "A": "Herbs",
            "B": "Shrubs",
            "C": "Trees",
            "not_sure": "Not sure",
        },
    ),
    _yn(
        "invasive_species",
        "questions_3",
        "Do you see plants that may be non-native or invasive?",
        "AI may suggest candidates only. Confirm with an expert before treating as certain.",
        "candidates_only",
    ),
    FieldDef(
        id="invasive_species_notes",
        group="questions_3",
        question="Which plants might be invasive? (optional notes)",
        help="Short free text for names you recognise. Never sent to the public FHIR server.",
        ai_role="human_only",
        value_type="text",
    ),
    _yn(
        "vegetation_cuts",
        "questions_3",
        "Have bank plants been cut recently?",
        "Fresh cut stems or cleared strips along the bank count as yes.",
        "suggest",
    ),
    FieldDef(
        id="overall_assessment",
        group="feedback",
        question="Overall, how healthy does this stream ecosystem seem?",
        help="Choose your rating before seeing the advisory comparison.",
        ai_role="human_only",
        value_type="choice",
        values=["good", "moderate", "poor"],
        value_labels={
            "good": "Good",
            "moderate": "Moderate",
            "poor": "Poor",
        },
    ),
    FieldDef(
        id="feelings",
        group="feedback",
        question="How does this place make you feel?",
        help="Rate joy, serenity, anger, and fear from 1 to 5, or mark Not applicable. Range assumed 1–5 until confirmed.",
        ai_role="human_only",
        value_type="feelings",
        pending=True,
        pending_note="Slider range assumed integers 1–5 with Not applicable.",
    ),
]

FIELDS_BY_ID: dict[str, FieldDef] = {field.id: field for field in FIELDS}

ANSWER_FIELD_IDS: frozenset[str] = frozenset(
    f.id
    for f in FIELDS
    if f.value_type in {"choice", "number", "text", "feelings"}
)


class FormSchemaResponse(BaseModel):
    version: str = "1"
    fields: list[FieldDef]
    pending_notes: dict[str, str] = Field(default_factory=dict)


def get_form_schema() -> FormSchemaResponse:
    pending_notes = {
        f.id: f.pending_note for f in FIELDS if f.pending and f.pending_note
    }
    return FormSchemaResponse(version="1", fields=list(FIELDS), pending_notes=pending_notes)


def validate_choice(field: FieldDef, value: Any) -> str | None:
    if field.values is None:
        return f"{field.id}: has no allowed values"
    if not isinstance(value, str):
        return f"{field.id}: expected a string choice"
    if value not in field.values:
        return f"{field.id}: '{value}' is not in {field.values}"
    return None


def validate_feelings(value: Any) -> str | None:
    if not isinstance(value, dict):
        return "feelings: expected an object with joy, serenity, anger, fear"
    for key in FEELINGS_KEYS:
        if key not in value:
            return f"feelings: missing '{key}'"
        entry = value[key]
        if not isinstance(entry, dict):
            return f"feelings.{key}: expected {{value, na}}"
        na = entry.get("na")
        raw = entry.get("value")
        if na is True:
            if raw is not None:
                return f"feelings.{key}: value must be null when na is true"
            continue
        if na is not False:
            return f"feelings.{key}: na must be true or false"
        if not isinstance(raw, int) or isinstance(raw, bool) or raw < 1 or raw > 5:
            return f"feelings.{key}: value must be an integer from 1 to 5"
    return None


def validate_answers(answers: dict[str, Any] | None) -> list[str]:
    """Return a list of validation error messages (empty if valid)."""
    if answers is None:
        return []
    if not isinstance(answers, dict):
        return ["answers must be an object"]

    errors: list[str] = []
    for field_id, value in answers.items():
        if value is None:
            continue
        field = FIELDS_BY_ID.get(field_id)
        if field is None or field.id not in ANSWER_FIELD_IDS:
            errors.append(f"unknown answer field: {field_id}")
            continue
        if field.value_type == "choice":
            err = validate_choice(field, value)
            if err:
                errors.append(err)
        elif field.value_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{field_id}: expected a number")
        elif field.value_type == "text":
            if not isinstance(value, str):
                errors.append(f"{field_id}: expected a string")
            elif len(value) > 2000:
                errors.append(f"{field_id}: text too long (max 2000)")
        elif field.value_type == "feelings":
            err = validate_feelings(value)
            if err:
                errors.append(err)
    return errors


def validate_field_sources(
    sources: dict[str, Any] | None,
    answers: dict[str, Any] | None = None,
) -> list[str]:
    if sources is None:
        return []
    if not isinstance(sources, dict):
        return ["field_sources must be an object"]
    errors: list[str] = []
    for field_id, source in sources.items():
        if field_id not in ANSWER_FIELD_IDS and field_id != "site":
            errors.append(f"unknown field_sources key: {field_id}")
            continue
        if source not in FIELD_SOURCES:
            errors.append(
                f"field_sources.{field_id}: must be one of {sorted(FIELD_SOURCES)}"
            )
    if answers:
        for field_id, value in answers.items():
            if value is None:
                continue
            if field_id in ANSWER_FIELD_IDS and field_id not in (sources or {}):
                # Source may be defaulted by the API; not an error here.
                pass
    return errors
