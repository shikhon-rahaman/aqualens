"""File-backed AI response cache keyed by sha256(image)+role."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from app.ai.models import RoleAnalysisResult
from app.ai.prompts import fields_for_role

logger = logging.getLogger(__name__)


def image_cache_key(image_bytes: bytes, role: str) -> str:
    digest = hashlib.sha256(image_bytes).hexdigest()
    return f"{digest}_{role}"


class CachedProvider:
    name = "cache"

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, image_bytes: bytes, role: str) -> Path:
        return self.cache_dir / f"{image_cache_key(image_bytes, role)}.json"

    def get(self, image_bytes: bytes, role: str) -> RoleAnalysisResult | None:
        path = self._path(image_bytes, role)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return RoleAnalysisResult.model_validate(data)
        except Exception as exc:
            logger.warning("cache read failed for %s: %s", path.name, exc)
            return None

    def put(self, image_bytes: bytes, role: str, result: RoleAnalysisResult) -> None:
        path = self._path(image_bytes, role)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    def analyze(self, image_bytes: bytes, role: str) -> RoleAnalysisResult:
        """Provider interface: raise on cache miss so the chain can continue."""
        fields_for_role(role)  # validate role
        hit = self.get(image_bytes, role)
        if hit is None:
            raise LookupError(f"cache miss for role={role}")
        return hit
