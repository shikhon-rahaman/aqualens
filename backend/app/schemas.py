"""Shared Pydantic request/response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    ai_chain: list[str]
    db: str


class SiteCreate(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1, max_length=64)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SiteOut(BaseModel):
    id: str
    name: str
    code: str
    lat: float
    lon: float
    is_demo: bool
    distance_m: float | None = None

    model_config = {"from_attributes": True}


class SitesListResponse(BaseModel):
    sites: list[SiteOut]


class EvaluateRequest(BaseModel):
    site_id: str | None = None
    user_lat: float | None = None
    user_lon: float | None = None
    facing_downstream: bool = True
    answers: dict[str, Any] = Field(default_factory=dict)
    field_sources: dict[str, str] = Field(default_factory=dict)
    ai_suggestions: dict[str, Any] = Field(default_factory=dict)
    unusable_photos: list[str] = Field(default_factory=list)
    include_context: bool = True


class EvaluateResponse(BaseModel):
    flags: list[dict[str, Any]] = Field(default_factory=list)
    needs_expert: bool
    overall_suggested: str
    overall_pressure_count: int
    overall_mismatch_levels: int | None = None
    risk: dict[str, Any]
    context: dict[str, Any]


class ObservationCreate(BaseModel):
    site_id: str
    facing_downstream: bool = True
    user_lat: float | None = None
    user_lon: float | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
    field_sources: dict[str, str] = Field(default_factory=dict)
    ai_suggestions: dict[str, Any] = Field(default_factory=dict)
    feelings: dict[str, Any] | None = None
    status: str = "confirmed"
    is_synthetic: bool = False
    needs_expert: bool | None = None
    overall_user: str | None = None
    overall_suggested: str | None = None
    risk_contact: str | None = None
    risk_ecosystem: str | None = None
    risk_reasons: dict[str, Any] | None = None
    flags: list[Any] | None = None
    skip_evaluation: bool = False


class ObservationSummary(BaseModel):
    id: str
    site_id: str
    site_name: str | None = None
    lat: float | None = None
    lon: float | None = None
    status: str
    needs_expert: bool
    risk_contact: str | None = None
    risk_ecosystem: str | None = None
    overall_user: str | None = None
    is_synthetic: bool
    captured_at: datetime


class ObservationOut(BaseModel):
    id: str
    site_id: str
    site_name: str | None = None
    site_lat: float | None = None
    site_lon: float | None = None
    user_lat: float | None = None
    user_lon: float | None = None
    facing_downstream: bool
    captured_at: datetime
    photos: dict[str, str] = Field(default_factory=dict)
    answers: dict[str, Any] = Field(default_factory=dict)
    ai_suggestions: dict[str, Any] = Field(default_factory=dict)
    field_sources: dict[str, str] = Field(default_factory=dict)
    flags: list[Any] = Field(default_factory=list)
    needs_expert: bool
    status: str
    overall_user: str | None = None
    overall_suggested: str | None = None
    risk_contact: str | None = None
    risk_ecosystem: str | None = None
    risk_reasons: dict[str, Any] | None = None
    feelings: dict[str, Any] | None = None
    is_synthetic: bool
    fhir_sent_at: datetime | None = None


class FhirExportResponse(BaseModel):
    bundle: dict[str, Any]
    excluded: list[str]
    fhir_version: str


class FhirSendResponse(BaseModel):
    ok: bool
    http_status: int
    server_response: dict[str, Any] | list[Any] | str | None = None
    fhir_sent_at: datetime | None = None
    excluded: list[str] = Field(default_factory=list)


class ObservationsListResponse(BaseModel):
    observations: list[ObservationSummary]
