"""Observation create, get, list, and evaluate endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Header, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.adapters.fhir_client import send_bundle
from app.adapters.storage import get_storage, new_observation_id
from app.config import Settings, get_settings
from app.db import get_db
from app.evaluation import evaluate_observation
from app.fhir_mapper import EXCLUDED_FROM_FHIR, fhir_export_payload
from app.form_schema import (
    ANSWER_FIELD_IDS,
    FIELD_SOURCES,
    validate_answers,
    validate_feelings,
    validate_field_sources,
)
from app.models import Observation, Site
from app.schemas import (
    EvaluateRequest,
    EvaluateResponse,
    FhirExportResponse,
    FhirSendResponse,
    ObservationCreate,
    ObservationOut,
    ObservationSummary,
    ObservationsListResponse,
)

router = APIRouter(prefix="/api", tags=["observations"])


def _default_sources(answers: dict[str, Any], sources: dict[str, str]) -> dict[str, str]:
    merged = dict(sources)
    for field_id, value in answers.items():
        if field_id not in ANSWER_FIELD_IDS:
            continue
        if field_id in merged:
            continue
        merged[field_id] = "human" if value is not None else "unanswered"
    for field_id in ANSWER_FIELD_IDS:
        merged.setdefault(field_id, "unanswered")
    return merged


def _observation_out(obs: Observation) -> ObservationOut:
    site = obs.site
    return ObservationOut(
        id=obs.id,
        site_id=obs.site_id,
        site_name=site.name if site else None,
        site_lat=site.lat if site else None,
        site_lon=site.lon if site else None,
        user_lat=obs.user_lat,
        user_lon=obs.user_lon,
        facing_downstream=obs.facing_downstream,
        captured_at=obs.captured_at,
        photos=dict(obs.photos_json or {}),
        answers=dict(obs.answers_json or {}),
        ai_suggestions=dict(obs.ai_suggestions_json or {}),
        field_sources=dict(obs.field_sources_json or {}),
        flags=list(obs.flags_json or []),
        needs_expert=obs.needs_expert,
        status=obs.status,
        overall_user=obs.overall_user,
        overall_suggested=obs.overall_suggested,
        risk_contact=obs.risk_contact,
        risk_ecosystem=obs.risk_ecosystem,
        risk_reasons=obs.risk_reasons_json,
        feelings=obs.feelings_json,
        is_synthetic=obs.is_synthetic,
        fhir_sent_at=obs.fhir_sent_at,
    )


def _parse_json_object(raw: str | None, field_name: str) -> dict[str, Any]:
    if raw is None or raw.strip() == "":
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be valid JSON",
        ) from exc
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must be a JSON object",
        )
    return data


def _run_evaluation(
    *,
    site: Site,
    answers: dict[str, Any],
    field_sources: dict[str, str],
    ai_suggestions: dict[str, Any],
    user_lat: float | None,
    user_lon: float | None,
    include_context: bool = True,
) -> dict[str, Any]:
    return evaluate_observation(
        answers,
        ai_suggestions=ai_suggestions,
        field_sources=field_sources,
        site_lat=site.lat,
        site_lon=site.lon,
        user_lat=user_lat,
        user_lon=user_lon,
        include_context=include_context,
    )


def _create_observation_record(
    db: Session,
    *,
    site_id: str,
    facing_downstream: bool,
    user_lat: float | None,
    user_lon: float | None,
    answers: dict[str, Any],
    field_sources: dict[str, str],
    ai_suggestions: dict[str, Any],
    feelings: dict[str, Any] | None,
    status_value: str,
    is_synthetic: bool,
    needs_expert: bool | None,
    overall_user: str | None,
    overall_suggested: str | None,
    risk_contact: str | None,
    risk_ecosystem: str | None,
    risk_reasons: dict[str, Any] | None,
    flags: list[Any] | None,
    photos: dict[str, str],
    observation_id: str | None = None,
    skip_evaluation: bool = False,
) -> Observation:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    answers = dict(answers)
    if feelings is None and "feelings" in answers:
        maybe = answers.pop("feelings")
        feelings = maybe if isinstance(maybe, dict) else None

    errors = validate_answers(answers)
    if feelings is not None:
        feel_err = validate_feelings(feelings)
        if feel_err:
            errors.append(feel_err)
    errors.extend(validate_field_sources(field_sources, answers))
    for source in field_sources.values():
        if source not in FIELD_SOURCES:
            errors.append(f"invalid field source: {source}")
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    sources = _default_sources(answers, field_sources)
    overall = overall_user or (
        answers.get("overall_assessment")
        if isinstance(answers.get("overall_assessment"), str)
        else None
    )

    eval_payload: dict[str, Any] | None = None
    if not skip_evaluation:
        # Skip live weather/water on create to keep save fast and offline-friendly;
        # rainfall can be re-fetched on evaluate. Risk still uses answers only.
        eval_payload = _run_evaluation(
            site=site,
            answers=answers,
            field_sources=sources,
            ai_suggestions=ai_suggestions,
            user_lat=user_lat,
            user_lon=user_lon,
            include_context=False,
        )

    if eval_payload is not None:
        flags = flags if flags is not None else eval_payload["flags"]
        needs_expert = (
            bool(needs_expert)
            if needs_expert is not None
            else bool(eval_payload["needs_expert"])
        )
        overall_suggested = overall_suggested or eval_payload["overall_suggested"]
        risk = eval_payload["risk"]
        risk_contact = risk_contact or risk["contact"]["level"]
        risk_ecosystem = risk_ecosystem or risk["ecosystem"]["level"]
        risk_reasons = risk_reasons or {
            "contact": risk["contact"]["reasons"],
            "ecosystem": risk["ecosystem"]["reasons"],
            "disclaimer": risk["disclaimer"],
        }
        if needs_expert and status_value == "confirmed":
            status_value = "flagged"
    else:
        needs_expert = bool(needs_expert) if needs_expert is not None else False

    obs = Observation(
        id=observation_id or new_observation_id(),
        site_id=site_id,
        user_lat=user_lat,
        user_lon=user_lon,
        facing_downstream=facing_downstream,
        captured_at=datetime.now(timezone.utc),
        photos_json=photos,
        answers_json=answers,
        ai_suggestions_json=ai_suggestions,
        field_sources_json=sources,
        flags_json=flags or [],
        needs_expert=needs_expert,
        status=status_value,
        overall_user=overall,
        overall_suggested=overall_suggested,
        risk_contact=risk_contact,
        risk_ecosystem=risk_ecosystem,
        risk_reasons_json=risk_reasons,
        feelings_json=feelings,
        is_synthetic=is_synthetic,
    )
    db.add(obs)
    db.commit()
    db.refresh(obs)
    _ = obs.site  # load relationship
    return obs


@router.post("/observations/evaluate", response_model=EvaluateResponse)
def evaluate_observation_endpoint(
    payload: EvaluateRequest,
    db: Session = Depends(get_db),
) -> EvaluateResponse:
    """Dry run: flags, risk notes, suggested overall. Does not save."""
    site: Site | None = None
    if payload.site_id:
        site = db.get(Site, payload.site_id)
        if site is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    result = evaluate_observation(
        payload.answers,
        ai_suggestions=payload.ai_suggestions,
        field_sources=payload.field_sources,
        site_lat=site.lat if site else None,
        site_lon=site.lon if site else None,
        user_lat=payload.user_lat,
        user_lon=payload.user_lon,
        unusable_photos=payload.unusable_photos,
        include_context=payload.include_context and site is not None,
    )
    return EvaluateResponse.model_validate(result)


@router.post(
    "/observations",
    response_model=ObservationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_observation_multipart(
    site_id: str = Form(...),
    facing_downstream: bool = Form(True),
    user_lat: float | None = Form(None),
    user_lon: float | None = Form(None),
    answers: str = Form("{}"),
    field_sources: str = Form("{}"),
    ai_suggestions: str = Form("{}"),
    feelings: str | None = Form(None),
    status_value: str = Form("confirmed", alias="status"),
    is_synthetic: bool = Form(False),
    needs_expert: bool | None = Form(None),
    overall_user: str | None = Form(None),
    overall_suggested: str | None = Form(None),
    photo_upstream: UploadFile | None = File(None),
    photo_downstream: UploadFile | None = File(None),
    photo_context: UploadFile | None = File(None),
    photo_biodiversity: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ObservationOut:
    answers_obj = _parse_json_object(answers, "answers")
    sources_obj = _parse_json_object(field_sources, "field_sources")
    suggestions_obj = _parse_json_object(ai_suggestions, "ai_suggestions")
    feelings_obj: dict[str, Any] | None = None
    if feelings is not None and feelings.strip() != "":
        feelings_obj = _parse_json_object(feelings, "feelings")

    observation_id = new_observation_id()
    storage = get_storage(settings)
    photos: dict[str, str] = {}
    uploads = {
        "upstream": photo_upstream,
        "downstream": photo_downstream,
        "context": photo_context,
        "biodiversity": photo_biodiversity,
    }
    for role, upload in uploads.items():
        if upload is None or not upload.filename:
            continue
        raw = await upload.read()
        if not raw:
            continue
        try:
            photos[role] = storage.save_photo(observation_id, role, raw)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not process photo '{role}': {exc}",
            ) from exc

    obs = _create_observation_record(
        db,
        site_id=site_id,
        facing_downstream=facing_downstream,
        user_lat=user_lat,
        user_lon=user_lon,
        answers=answers_obj,
        field_sources={k: str(v) for k, v in sources_obj.items()},
        ai_suggestions=suggestions_obj,
        feelings=feelings_obj,
        status_value=status_value,
        is_synthetic=is_synthetic,
        needs_expert=needs_expert,
        overall_user=overall_user,
        overall_suggested=overall_suggested,
        risk_contact=None,
        risk_ecosystem=None,
        risk_reasons=None,
        flags=None,
        photos=photos,
        observation_id=observation_id,
    )
    return _observation_out(obs)


@router.post(
    "/observations/json",
    response_model=ObservationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_observation_json(
    payload: ObservationCreate,
    db: Session = Depends(get_db),
) -> ObservationOut:
    """JSON create without photo upload (tests and seed scripts)."""
    obs = _create_observation_record(
        db,
        site_id=payload.site_id,
        facing_downstream=payload.facing_downstream,
        user_lat=payload.user_lat,
        user_lon=payload.user_lon,
        answers=payload.answers,
        field_sources=payload.field_sources,
        ai_suggestions=payload.ai_suggestions,
        feelings=payload.feelings,
        status_value=payload.status,
        is_synthetic=payload.is_synthetic,
        needs_expert=payload.needs_expert,
        overall_user=payload.overall_user,
        overall_suggested=payload.overall_suggested,
        risk_contact=payload.risk_contact,
        risk_ecosystem=payload.risk_ecosystem,
        risk_reasons=payload.risk_reasons,
        flags=payload.flags,
        photos={},
        skip_evaluation=payload.skip_evaluation,
    )
    return _observation_out(obs)


@router.get("/observations", response_model=ObservationsListResponse)
def list_observations(
    bbox: str | None = Query(
        default=None,
        description="minLon,minLat,maxLon,maxLat",
    ),
    needs_expert: bool | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> ObservationsListResponse:
    stmt = select(Observation).options(joinedload(Observation.site))
    if needs_expert is not None:
        stmt = stmt.where(Observation.needs_expert.is_(needs_expert))
    if status_filter is not None:
        stmt = stmt.where(Observation.status == status_filter)

    observations = list(db.scalars(stmt).unique().all())

    if bbox:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            min_lon, min_lat, max_lon, max_lat = parts
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="bbox must be minLon,minLat,maxLon,maxLat",
            ) from exc

        def in_box(obs: Observation) -> bool:
            site = obs.site
            if site is None:
                return False
            return min_lon <= site.lon <= max_lon and min_lat <= site.lat <= max_lat

        observations = [o for o in observations if in_box(o)]

    summaries = [
        ObservationSummary(
            id=o.id,
            site_id=o.site_id,
            site_name=o.site.name if o.site else None,
            lat=o.site.lat if o.site else None,
            lon=o.site.lon if o.site else None,
            status=o.status,
            needs_expert=o.needs_expert,
            risk_contact=o.risk_contact,
            risk_ecosystem=o.risk_ecosystem,
            overall_user=o.overall_user,
            is_synthetic=o.is_synthetic,
            captured_at=o.captured_at,
        )
        for o in observations
    ]
    summaries.sort(key=lambda s: s.captured_at, reverse=True)
    return ObservationsListResponse(observations=summaries)


@router.get("/observations/{observation_id}", response_model=ObservationOut)
def get_observation(
    observation_id: str,
    db: Session = Depends(get_db),
) -> ObservationOut:
    obs = db.scalar(
        select(Observation)
        .options(joinedload(Observation.site))
        .where(Observation.id == observation_id)
    )
    if obs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found")
    return _observation_out(obs)


def _load_observation(db: Session, observation_id: str) -> Observation:
    obs = db.scalar(
        select(Observation)
        .options(joinedload(Observation.site))
        .where(Observation.id == observation_id)
    )
    if obs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found")
    return obs


@router.get("/observations/{observation_id}/fhir", response_model=FhirExportResponse)
def get_observation_fhir(
    observation_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FhirExportResponse:
    obs = _load_observation(db, observation_id)
    payload = fhir_export_payload(obs, settings)
    return FhirExportResponse.model_validate(payload)


@router.post("/observations/{observation_id}/fhir/send", response_model=FhirSendResponse)
def send_observation_fhir(
    observation_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FhirSendResponse:
    obs = _load_observation(db, observation_id)
    payload = fhir_export_payload(obs, settings)
    result = send_bundle(settings.fhir_server_url, payload["bundle"])
    sent_at = None
    if result["ok"]:
        sent_at = datetime.now(timezone.utc)
        obs.fhir_sent_at = sent_at
        db.add(obs)
        db.commit()
        db.refresh(obs)
    return FhirSendResponse(
        ok=bool(result["ok"]),
        http_status=int(result["http_status"]),
        server_response=result.get("server_response"),
        fhir_sent_at=sent_at,
        excluded=list(EXCLUDED_FROM_FHIR),
    )


def _verify_expert_pin(pin: str | None, settings: Settings) -> None:
    """Verify expert PIN. Demo-only authentication."""
    if pin != settings.expert_pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing expert PIN",
        )


@router.get("/queue", response_model=ObservationsListResponse)
def get_expert_queue(
    x_expert_pin: str | None = Header(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ObservationsListResponse:
    """Get observations needing expert review. Requires X-Expert-Pin header."""
    _verify_expert_pin(x_expert_pin, settings)

    stmt = (
        select(Observation)
        .options(joinedload(Observation.site))
        .where(Observation.needs_expert.is_(True))
        .order_by(Observation.captured_at.desc())
    )
    observations = list(db.scalars(stmt).unique())

    summaries = [
        ObservationSummary(
            id=o.id,
            site_id=o.site_id,
            site_name=o.site.name if o.site else None,
            lat=o.site.lat if o.site else None,
            lon=o.site.lon if o.site else None,
            status=o.status,
            needs_expert=o.needs_expert,
            risk_contact=o.risk_contact,
            risk_ecosystem=o.risk_ecosystem,
            overall_user=o.overall_user,
            is_synthetic=o.is_synthetic,
            captured_at=o.captured_at,
        )
        for o in observations
    ]
    return ObservationsListResponse(observations=summaries)


@router.post("/observations/{observation_id}/review", response_model=ObservationOut)
async def expert_review_observation(
    observation_id: str,
    action: str = Form(...),  # "approve" or "correct"
    answers: str | None = Form(None),  # Only for "correct"
    field_sources: str | None = Form(None),  # Only for "correct"
    x_expert_pin: str | None = Header(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ObservationOut:
    """Expert review: approve or correct an observation. Requires X-Expert-Pin header."""
    _verify_expert_pin(x_expert_pin, settings)

    obs = _load_observation(db, observation_id)

    if action == "approve":
        obs.status = "expert_approved"
        obs.needs_expert = False
        db.add(obs)
        db.commit()
        db.refresh(obs)
    elif action == "correct":
        if not answers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="answers required for correct action",
            )
        answers_obj = _parse_json_object(answers, "answers")
        sources_obj = _parse_json_object(field_sources or "{}", "field_sources")

        # Update answers and sources
        obs.answers_json = answers_obj
        obs.field_sources_json = _default_sources(answers_obj, sources_obj)

        # Re-evaluate
        site = obs.site
        if site:
            eval_result = _run_evaluation(
                site=site,
                answers=answers_obj,
                field_sources=obs.field_sources_json,
                ai_suggestions=obs.ai_suggestions_json or {},
                user_lat=obs.user_lat,
                user_lon=obs.user_lon,
                include_context=True,
            )
            obs.flags_json = eval_result.get("flags", [])
            obs.needs_expert = eval_result.get("needs_expert", False)
            obs.overall_suggested = eval_result.get("overall_suggested")
            obs.risk_contact = eval_result["risk"]["contact"]["level"]
            obs.risk_ecosystem = eval_result["risk"]["ecosystem"]["level"]
            obs.risk_reasons_json = eval_result["risk"]

        obs.status = "expert_corrected"
        db.add(obs)
        db.commit()
        db.refresh(obs)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="action must be 'approve' or 'correct'",
        )

    return _observation_out(obs)
