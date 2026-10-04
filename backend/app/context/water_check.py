"""Overpass waterway proximity check (within 100 m).

Unknown must never create a validation flag — callers treat "unknown" as no signal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_TIMEOUT_S = 8.0
DEFAULT_RADIUS_M = 100
WaterNearby = Literal["yes", "no", "unknown"]


@dataclass(frozen=True)
class WaterCheckResult:
    water_nearby: WaterNearby
    error: str | None = None


def check_waterway_nearby(
    lat: float,
    lon: float,
    *,
    radius_m: int = DEFAULT_RADIUS_M,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    client: httpx.Client | None = None,
) -> WaterCheckResult:
    """Return yes/no/unknown. Failures → unknown (never invent a flag)."""
    query = (
        f"[out:json][timeout:{int(max(1, timeout_s))}];\n"
        f"(\n"
        f'  way["waterway"](around:{radius_m},{lat},{lon});\n'
        f'  relation["waterway"](around:{radius_m},{lat},{lon});\n'
        f'  way["natural"="water"](around:{radius_m},{lat},{lon});\n'
        f");\n"
        f"out ids;"
    )
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout_s)
    try:
        response = http.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=timeout_s,
        )
        response.raise_for_status()
        payload = response.json()
        elements = payload.get("elements") if isinstance(payload, dict) else None
        if not isinstance(elements, list):
            return WaterCheckResult(water_nearby="unknown", error="unexpected Overpass payload")
        return WaterCheckResult(water_nearby="yes" if elements else "no")
    except Exception as exc:
        logger.warning("water check failed: %s", exc)
        return WaterCheckResult(water_nearby="unknown", error=str(exc))
    finally:
        if owns_client:
            http.close()
