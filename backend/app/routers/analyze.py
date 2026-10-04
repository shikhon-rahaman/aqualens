"""POST /api/analyze — AI suggestions only; never saves."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile

from app.ai.chain import ProviderChain
from app.ai.service import analyze_photos
from app.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["analyze"])


def get_chain(settings: Settings = Depends(get_settings)) -> ProviderChain:
    return ProviderChain(settings=settings)


@router.post("/analyze")
async def analyze(
    photo_upstream: UploadFile | None = File(None),
    photo_downstream: UploadFile | None = File(None),
    photo_context: UploadFile | None = File(None),
    photo_biodiversity: UploadFile | None = File(None),
    settings: Settings = Depends(get_settings),
    chain: ProviderChain = Depends(get_chain),
) -> dict:
    photos: dict[str, bytes] = {}
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
        if raw:
            photos[role] = raw

    sleep = settings.sleep_seconds > 0 and "groq" in settings.ai_chain_list
    return analyze_photos(photos, chain=chain, settings=settings, sleep_between=sleep)
