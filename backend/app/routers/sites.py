"""Sites list, nearest-by-GPS, and create."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.geo import haversine_m
from app.models import Site
from app.schemas import SiteCreate, SiteOut, SitesListResponse

router = APIRouter(prefix="/api", tags=["sites"])


@router.get("/sites", response_model=SitesListResponse)
def list_sites(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    db: Session = Depends(get_db),
) -> SitesListResponse:
    if (lat is None) ^ (lon is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide both lat and lon, or neither",
        )

    sites = list(db.scalars(select(Site)).all())
    items: list[SiteOut] = []
    for site in sites:
        distance: float | None = None
        if lat is not None and lon is not None:
            distance = round(haversine_m(lat, lon, site.lat, site.lon), 1)
        items.append(
            SiteOut(
                id=site.id,
                name=site.name,
                code=site.code,
                lat=site.lat,
                lon=site.lon,
                is_demo=site.is_demo,
                distance_m=distance,
            )
        )

    if lat is not None and lon is not None:
        items.sort(key=lambda s: s.distance_m if s.distance_m is not None else float("inf"))
    else:
        items.sort(key=lambda s: s.code)

    return SitesListResponse(sites=items)


@router.post("/sites", response_model=SiteOut, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, db: Session = Depends(get_db)) -> SiteOut:
    site = Site(
        name=payload.name.strip(),
        code=payload.code.strip(),
        lat=payload.lat,
        lon=payload.lon,
        is_demo=False,
    )
    db.add(site)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site code '{payload.code}' already exists",
        ) from exc
    db.refresh(site)
    return SiteOut(
        id=site.id,
        name=site.name,
        code=site.code,
        lat=site.lat,
        lon=site.lon,
        is_demo=site.is_demo,
        distance_m=None,
    )
