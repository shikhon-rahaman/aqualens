"""Groq vision provider."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

from app.ai.models import RoleAnalysisResult, parse_model_json, validate_role_payload
from app.ai.prompts import SYSTEM_PROMPT, fields_for_role, user_prompt_for_role
from app.config import Settings

logger = logging.getLogger(__name__)


class GroqProvider:
    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        if not settings.groq_vision_model:
            raise RuntimeError("GROQ_VISION_MODEL is not set")
        from groq import Groq

        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_vision_model

    def analyze(self, image_bytes: bytes, role: str) -> RoleAnalysisResult:
        field_ids = fields_for_role(role)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt_for_role(role)},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            },
        ]

        response = self._create_with_retry(messages)
        usage = getattr(response, "usage", None)
        if usage is not None:
            logger.info(
                "groq tokens role=%s prompt=%s completion=%s total=%s",
                role,
                getattr(usage, "prompt_tokens", None),
                getattr(usage, "completion_tokens", None),
                getattr(usage, "total_tokens", None),
            )

        content = response.choices[0].message.content or ""
        data = parse_model_json(content)
        return validate_role_payload(role, field_ids, data)

    def _create_with_retry(self, messages: list[dict[str, Any]]) -> Any:
        try:
            return self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            if not _is_rate_limit(exc):
                raise
            logger.warning("groq rate limited; retrying once after short wait")
            time.sleep(min(5.0, max(1.0, self.settings.sleep_seconds / 6)))
            return self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return "rate" in name or "429" in text or "rate_limit" in text
