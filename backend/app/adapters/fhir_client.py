"""HTTP client for posting FHIR Bundles to FHIR_SERVER_URL (no fhir.resources imports)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 30.0


def send_bundle(
    server_url: str,
    bundle: dict[str, Any],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """POST a transaction Bundle. Returns ok/http_status/server_response."""
    base = server_url.rstrip("/")
    owns = client is None
    http = client or httpx.Client(timeout=timeout_s)
    try:
        response = http.post(
            base,
            json=bundle,
            headers={
                "Content-Type": "application/fhir+json",
                "Accept": "application/fhir+json",
            },
            timeout=timeout_s,
        )
        body: Any
        try:
            body = response.json()
        except Exception:
            body = {"raw": response.text[:4000]}
        ok = 200 <= response.status_code < 300
        if not ok:
            logger.warning(
                "FHIR send failed status=%s body=%s",
                response.status_code,
                str(body)[:500],
            )
        return {
            "ok": ok,
            "http_status": response.status_code,
            "server_response": body,
        }
    except Exception as exc:
        logger.warning("FHIR send error: %s", exc)
        return {
            "ok": False,
            "http_status": 0,
            "server_response": {"error": str(exc)},
        }
    finally:
        if owns:
            http.close()
