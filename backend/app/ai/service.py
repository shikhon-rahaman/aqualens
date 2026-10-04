"""Orchestrate per-role analysis and merge (never persists)."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.adapters.storage import resize_and_strip_exif
from app.ai.chain import ProviderChain
from app.ai.merge import merge_stream_pair
from app.ai.models import FieldSuggestion
from app.config import Settings

logger = logging.getLogger(__name__)

PHOTO_ROLES = ("upstream", "downstream", "context", "biodiversity")


def analyze_photos(
    photos: dict[str, bytes],
    *,
    chain: ProviderChain,
    settings: Settings,
    sleep_between: bool = True,
) -> dict[str, Any]:
    """Analyze uploaded photos by role and return the API payload shape."""
    prepared: dict[str, bytes] = {}
    for role, raw in photos.items():
        if role not in PHOTO_ROLES or not raw:
            continue
        prepared[role] = resize_and_strip_exif(raw)

    if not prepared:
        return {
            "status": "ai_unavailable",
            "suggestions": {},
            "message": "AI is unavailable; please answer manually.",
            "needs_expert_hints": [],
            "provider_used": None,
        }

    role_results = {}
    providers_used: list[str] = []
    any_success = False

    for index, role in enumerate(PHOTO_ROLES):
        if role not in prepared:
            continue
        if sleep_between and index > 0 and settings.sleep_seconds > 0:
            # Protect free-tier TPM when Groq is in the chain.
            if "groq" in chain.provider_names:
                time.sleep(settings.sleep_seconds)
        result, provider_name = chain.analyze(prepared[role], role)
        if result is None:
            continue
        any_success = True
        role_results[role] = result
        if provider_name:
            providers_used.append(f"{role}:{provider_name}")

    if not any_success:
        return {
            "status": "ai_unavailable",
            "suggestions": {},
            "message": "AI is unavailable; please answer manually.",
            "needs_expert_hints": [],
            "provider_used": None,
        }

    suggestions: dict[str, FieldSuggestion] = {}
    needs_expert: list[str] = []

    merged, note, stream_hints = merge_stream_pair(
        role_results.get("upstream"),
        role_results.get("downstream"),
    )
    suggestions.update(merged)
    needs_expert.extend(stream_hints)

    for role in ("context", "biodiversity"):
        result = role_results.get(role)
        if result is None:
            continue
        suggestions.update(result.suggestions)
        for field_id in ("construction",):
            s = result.suggestions.get(field_id)
            if s and s.value == "yes" and field_id not in needs_expert:
                needs_expert.append(field_id)

    return {
        "status": "ok",
        "suggestions": {
            field_id: suggestion.model_dump()
            for field_id, suggestion in suggestions.items()
        },
        "upstream_vs_downstream": note,
        "needs_expert_hints": needs_expert,
        "provider_used": ",".join(providers_used) if providers_used else "unknown",
        "roles_analyzed": sorted(role_results.keys()),
    }
