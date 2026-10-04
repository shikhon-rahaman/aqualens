"""AI provider chain: try each provider in AI_PROVIDER_CHAIN order."""

from __future__ import annotations

import logging
from pathlib import Path

from app.ai.cache_provider import CachedProvider
from app.ai.groq_provider import GroqProvider
from app.ai.mock_provider import MockProvider
from app.ai.models import RoleAnalysisResult
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ProviderChain:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        mock: MockProvider | None = None,
        cache: CachedProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        cache_dir = Path(self.settings.ai_cache_dir)
        if not cache_dir.is_absolute():
            cache_dir = Path.cwd() / cache_dir
        self.cache = cache or CachedProvider(cache_dir)
        self.mock = mock or MockProvider()
        self.provider_names = [
            part.strip()
            for part in self.settings.ai_provider_chain.split(",")
            if part.strip()
        ]

    def analyze(self, image_bytes: bytes, role: str) -> tuple[RoleAnalysisResult | None, str | None]:
        """Return (result, provider_name). Both None if every provider fails."""
        errors: list[str] = []
        for name in self.provider_names:
            try:
                result = self._run_one(name, image_bytes, role)
            except Exception as exc:
                logger.warning("AI provider %s failed for role=%s: %s", name, role, exc)
                errors.append(f"{name}: {exc}")
                continue
            if name != "cache":
                try:
                    self.cache.put(image_bytes, role, result)
                except Exception as exc:
                    logger.warning("failed to write AI cache: %s", exc)
            return result, name
        logger.error("all AI providers failed: %s", "; ".join(errors))
        return None, None

    def _run_one(self, name: str, image_bytes: bytes, role: str) -> RoleAnalysisResult:
        if name == "groq":
            return GroqProvider(self.settings).analyze(image_bytes, role)
        if name == "cache":
            return self.cache.analyze(image_bytes, role)
        if name == "mock":
            return self.mock.analyze(image_bytes, role)
        raise ValueError(f"unknown AI provider in chain: {name}")


def get_provider_chain(settings: Settings | None = None) -> ProviderChain:
    return ProviderChain(settings=settings)
