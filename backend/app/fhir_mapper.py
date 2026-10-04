"""Build FHIR R4B transaction Bundles from AquaLens observations.

All fhir.resources imports live in this file only (Prompt 5).
Package fhir.resources 8.x exposes R4B (no separate R4 module); HAPI baseR4
accepts these resource shapes for the public test server.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fhir.resources.R4B.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.annotation import Annotation
from fhir.resources.R4B.location import Location, LocationPosition
from fhir.resources.R4B.meta import Meta
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.provenance import Provenance, ProvenanceAgent
from fhir.resources.R4B.quantity import Quantity
from fhir.resources.R4B.reference import Reference

from app.config import Settings
from app.form_schema import FIELDS_BY_ID
from app.models import Observation as ObservationRow
from app.risk import DISCLAIMER

# Never export these to the public FHIR test server.
EXCLUDED_FROM_FHIR = ("photos", "feelings", "free_text")
FREE_TEXT_FIELD_IDS = frozenset({"invasive_species_notes"})
SKIP_ANSWER_FIELD_IDS = frozenset(
    {"feelings", "overall_assessment", *FREE_TEXT_FIELD_IDS}
)

FHIR_VERSION_USED = "R4B"
SURVEY_CATEGORY = CodeableConcept(
    coding=[
        Coding(
            system="http://terminology.hl7.org/CodeSystem/observation-category",
            code="survey",
            display="Survey",
        )
    ]
)


def _iso(dt: datetime | None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _code(system: str, code: str, display: str | None = None) -> CodeableConcept:
    return CodeableConcept(
        coding=[Coding(system=system, code=str(code), display=display or str(code))]
    )


def _answered_fields(answers: dict[str, Any]) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    for field_id, value in answers.items():
        if value is None:
            continue
        if field_id in SKIP_ANSWER_FIELD_IDS:
            continue
        if field_id not in FIELDS_BY_ID:
            continue
        field = FIELDS_BY_ID[field_id]
        if field.value_type == "text":
            continue
        if field.value_type == "feelings":
            continue
        items.append((field_id, value))
    items.sort(key=lambda pair: pair[0])
    return items


def _note_text(
    field_id: str,
    ai_suggestions: dict[str, Any],
    reviewer_note: str | None = None,
) -> str | None:
    if reviewer_note and reviewer_note.strip():
        return reviewer_note.strip()
    raw = ai_suggestions.get(field_id)
    if isinstance(raw, dict):
        reason = raw.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None


def build_location(site_id: str, name: str, lat: float, lon: float, code: str | None) -> Location:
    return Location(
        id=site_id,
        meta=Meta(source="AquaLens"),
        name=name,
        status="active",
        description=f"AquaLens site code {code}" if code else "AquaLens site",
        position=LocationPosition(latitude=lat, longitude=lon),
    )


def build_field_observation(
    *,
    obs_id: str,
    field_id: str,
    value: Any,
    location_ref: str,
    effective: str,
    codesystem: str,
    note: str | None,
) -> Observation:
    field = FIELDS_BY_ID.get(field_id)
    display = field.question if field else field_id
    observation = Observation(
        id=obs_id,
        status="final",
        category=[SURVEY_CATEGORY],
        code=_code(codesystem, field_id, display),
        subject=Reference(reference=location_ref),
        effectiveDateTime=effective,
    )
    if field and field.value_type == "number":
        observation.valueQuantity = Quantity(
            value=float(value),
            unit="cm (unit to be confirmed)",
            system="http://unitsofmeasure.org",
            code="cm",
        )
    else:
        label = None
        if field and field.value_labels:
            label = field.value_labels.get(str(value))
        observation.valueCodeableConcept = _code(
            f"{codesystem}/Value/{field_id}", str(value), label
        )
    if note:
        observation.note = [Annotation(text=note)]
    return observation


def build_risk_observation(
    *,
    obs_id: str,
    code: str,
    level: str,
    location_ref: str,
    effective: str,
    codesystem: str,
    reasons: list[str] | None,
) -> Observation:
    note_parts = list(reasons or [])
    note_parts.append(DISCLAIMER)
    return Observation(
        id=obs_id,
        status="final",
        category=[SURVEY_CATEGORY],
        code=_code(codesystem, code, code.replace("_", " ")),
        subject=Reference(reference=location_ref),
        effectiveDateTime=effective,
        valueCodeableConcept=_code(f"{codesystem}/RiskLevel", level, level),
        note=[Annotation(text="; ".join(note_parts))],
    )


def build_provenance(
    *,
    prov_id: str,
    target_ref: str,
    source: str,
    recorded: str,
    codesystem: str,
) -> Provenance:
    return Provenance(
        id=prov_id,
        target=[Reference(reference=target_ref)],
        recorded=recorded,
        activity=_code(f"{codesystem}/FieldSource", source, source),
        agent=[
            ProvenanceAgent(
                type=_code(
                    "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                    "author",
                    "Author",
                ),
                who=Reference(display="AquaLens citizen (no personal identifiers)"),
            )
        ],
    )


def observation_row_to_bundle(
    row: ObservationRow,
    settings: Settings,
    *,
    fixed_ids: dict[str, str] | None = None,
) -> Bundle:
    """Build a privacy-safe transaction Bundle (no photos, feelings, or free text)."""
    codesystem = settings.fhir_codesystem_url
    site = row.site
    if site is None:
        raise ValueError("Observation must have a loaded site relationship")

    answers = dict(row.answers_json or {})
    sources = dict(row.field_sources_json or {})
    ai_suggestions = dict(row.ai_suggestions_json or {})
    risk_reasons = dict(row.risk_reasons_json or {}) if row.risk_reasons_json else {}
    effective = _iso(row.captured_at)

    def nid(key: str) -> str:
        if fixed_ids and key in fixed_ids:
            return fixed_ids[key]
        return str(uuid4())

    location_id = nid("location")
    location_full = f"urn:uuid:{location_id}"
    location = build_location(location_id, site.name, site.lat, site.lon, site.code)

    entries: list[BundleEntry] = [
        BundleEntry(
            fullUrl=location_full,
            resource=location,
            request=BundleEntryRequest(method="POST", url="Location"),
        )
    ]

    location_ref = location_full

    # Field observations + provenance
    for field_id, value in _answered_fields(answers):
        source = sources.get(field_id, "human")
        if source == "unanswered":
            continue
        obs_id = nid(f"obs:{field_id}")
        obs_full = f"urn:uuid:{obs_id}"
        note = _note_text(field_id, ai_suggestions)
        fhir_obs = build_field_observation(
            obs_id=obs_id,
            field_id=field_id,
            value=value,
            location_ref=location_ref,
            effective=effective,
            codesystem=codesystem,
            note=note,
        )
        entries.append(
            BundleEntry(
                fullUrl=obs_full,
                resource=fhir_obs,
                request=BundleEntryRequest(method="POST", url="Observation"),
            )
        )
        if source in {"ai_accepted", "ai_edited", "human"}:
            prov_id = nid(f"prov:{field_id}")
            provenance = build_provenance(
                prov_id=prov_id,
                target_ref=obs_full,
                source=source,
                recorded=effective,
                codesystem=codesystem,
            )
            entries.append(
                BundleEntry(
                    fullUrl=f"urn:uuid:{prov_id}",
                    resource=provenance,
                    request=BundleEntryRequest(method="POST", url="Provenance"),
                )
            )

    # Overall rating observation
    overall = row.overall_user or answers.get("overall_assessment")
    if isinstance(overall, str) and overall:
        oid = nid("obs:overall")
        ofull = f"urn:uuid:{oid}"
        entries.append(
            BundleEntry(
                fullUrl=ofull,
                resource=build_field_observation(
                    obs_id=oid,
                    field_id="overall_assessment",
                    value=overall,
                    location_ref=location_ref,
                    effective=effective,
                    codesystem=codesystem,
                    note=f"Advisory suggested: {row.overall_suggested}"
                    if row.overall_suggested
                    else None,
                ),
                request=BundleEntryRequest(method="POST", url="Observation"),
            )
        )

    # Risk observations
    for code, level, reason_key in (
        ("risk_contact", row.risk_contact, "contact"),
        ("risk_ecosystem", row.risk_ecosystem, "ecosystem"),
    ):
        if not level:
            continue
        rid = nid(f"obs:{code}")
        reasons = risk_reasons.get(reason_key)
        if not isinstance(reasons, list):
            reasons = []
        entries.append(
            BundleEntry(
                fullUrl=f"urn:uuid:{rid}",
                resource=build_risk_observation(
                    obs_id=rid,
                    code=code,
                    level=str(level),
                    location_ref=location_ref,
                    effective=effective,
                    codesystem=codesystem,
                    reasons=[str(r) for r in reasons],
                ),
                request=BundleEntryRequest(method="POST", url="Observation"),
            )
        )

    bundle = Bundle(
        id=nid("bundle"),
        type="transaction",
        timestamp=_iso(datetime.now(timezone.utc)) if not fixed_ids else effective,
        entry=entries,
    )
    # Round-trip validate with the library.
    return Bundle.model_validate(bundle.model_dump(mode="json", exclude_none=True, by_alias=True))


def bundle_to_dict(bundle: Bundle) -> dict[str, Any]:
    return bundle.model_dump(mode="json", exclude_none=True, by_alias=True)


def fhir_export_payload(row: ObservationRow, settings: Settings) -> dict[str, Any]:
    bundle = observation_row_to_bundle(row, settings)
    return {
        "bundle": bundle_to_dict(bundle),
        "excluded": list(EXCLUDED_FROM_FHIR),
        "fhir_version": FHIR_VERSION_USED,
    }


def assert_bundle_privacy(bundle_dict: dict[str, Any]) -> None:
    """Raise AssertionError if photos, feelings, or free text leaked into the bundle."""
    blob = str(bundle_dict).lower()
    for banned in ("feelings", "joy", "serenity", "anger", "fear", "/uploads/", "invasive_species_notes"):
        # Allow risk/disclaimer prose; block structured feelings keys and photo paths.
        if banned in {"joy", "serenity", "anger", "fear"}:
            # Only fail if they appear as field codes in coding
            if f"'code': '{banned}'" in blob or f'"code": "{banned}"' in blob:
                raise AssertionError(f"privacy leak: {banned}")
            continue
        if banned in blob and banned != "feelings":
            # "feelings" might appear in disclaimer? Unlikely. Check coding codes.
            pass
    # Structural scan of resources
    for entry in bundle_dict.get("entry") or []:
        resource = entry.get("resource") or {}
        if resource.get("resourceType") != "Observation":
            continue
        codings = ((resource.get("code") or {}).get("coding")) or []
        for coding in codings:
            code = coding.get("code")
            if code in FREE_TEXT_FIELD_IDS or code == "feelings":
                raise AssertionError(f"privacy leak field in FHIR: {code}")
            if code in {"joy", "serenity", "anger", "fear"}:
                raise AssertionError(f"privacy leak feeling: {code}")
        # Notes must not contain free-text invasive notes payload as structured export of that field
    if "invasive_species_notes" in blob:
        raise AssertionError("privacy leak: invasive_species_notes")
    if "/uploads/" in blob:
        raise AssertionError("privacy leak: photo path")
