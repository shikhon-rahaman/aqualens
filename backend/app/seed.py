"""Seed clearly labelled DEMO sites (not official OneAquaHealth sites)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Site

# Fictional cluster near a generic urban park — DEMO codes only.
DEMO_SITES: list[dict[str, float | str | bool]] = [
    {
        "code": "DEMO-01",
        "name": "DEMO Creek North (synthetic)",
        "lat": 12.9716,
        "lon": 77.5946,
        "is_demo": True,
    },
    {
        "code": "DEMO-02",
        "name": "DEMO Creek Bend (synthetic)",
        "lat": 12.9750,
        "lon": 77.5980,
        "is_demo": True,
    },
    {
        "code": "DEMO-03",
        "name": "DEMO Wetland Edge (synthetic)",
        "lat": 12.9680,
        "lon": 77.5900,
        "is_demo": True,
    },
    {
        "code": "DEMO-04",
        "name": "DEMO Canal Bridge (synthetic)",
        "lat": 12.9800,
        "lon": 77.6010,
        "is_demo": True,
    },
    {
        "code": "DEMO-05",
        "name": "DEMO Park Outfall (synthetic)",
        "lat": 12.9650,
        "lon": 77.6050,
        "is_demo": True,
    },
    {
        "code": "DEMO-06",
        "name": "DEMO Upstream Reach (synthetic)",
        "lat": 12.9735,
        "lon": 77.5850,
        "is_demo": True,
    },
]


def seed_demo_sites(db: Session) -> int:
    """Insert missing DEMO sites. Returns number of rows inserted."""
    inserted = 0
    for row in DEMO_SITES:
        code = str(row["code"])
        exists = db.scalar(select(Site).where(Site.code == code))
        if exists is not None:
            continue
        db.add(
            Site(
                name=str(row["name"]),
                code=code,
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                is_demo=bool(row["is_demo"]),
            )
        )
        inserted += 1
    if inserted:
        db.commit()
    return inserted
