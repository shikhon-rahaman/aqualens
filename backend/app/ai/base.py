"""AI provider protocol."""

from __future__ import annotations

from typing import Protocol

from app.ai.models import RoleAnalysisResult


class AIProvider(Protocol):
    name: str

    def analyze(self, image_bytes: bytes, role: str) -> RoleAnalysisResult:
        """Analyze one resized JPEG and return validated field suggestions."""
