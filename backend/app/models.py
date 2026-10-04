"""SQLAlchemy models for sites, observations and reviews."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    observations: Mapped[list[Observation]] = relationship(back_populates="site")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    site_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sites.id"), nullable=False
    )
    user_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    facing_downstream: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    photos_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    answers_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_suggestions_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    field_sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    flags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    needs_expert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    overall_user: Mapped[str | None] = mapped_column(String(32), nullable=True)
    overall_suggested: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_ecosystem: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_reasons_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feelings_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fhir_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    site: Mapped[Site] = relationship(back_populates="observations")
    reviews: Mapped[list[Review]] = relationship(back_populates="observation")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    observation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("observations.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    corrections_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    observation: Mapped[Observation] = relationship(back_populates="reviews")
