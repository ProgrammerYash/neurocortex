"""Groq provider readiness (cached)."""

from __future__ import annotations

import time
from typing import Any

from app.config import get_settings

_CACHE: dict[str, Any] = {"expires_at": 0.0, "payload": None}
_CACHE_TTL_SECONDS = 60.0


def _base_payload(*, configured: bool, status: str, model: str | None = None) -> dict[str, Any]:
    return {
        "configured": configured,
        "provider": "Groq",
        "status": status,
        "model": model,
    }


def get_groq_provider_status(*, force_refresh: bool = False) -> dict[str, Any]:
    now = time.time()
    if not force_refresh and _CACHE["payload"] is not None and now < _CACHE["expires_at"]:
        return dict(_CACHE["payload"])

    settings = get_settings()
    api_key = (settings.groq_api_key or "").strip()
    model = (settings.groq_model or "").strip()
    if not api_key or not model:
        payload = _base_payload(configured=False, status="not_configured", model=model or None)
    else:
        try:
            from groq import Groq

            client = Groq(api_key=api_key, timeout=settings.groq_timeout_seconds)
            # Lightweight validation: client constructs without network when key format is invalid.
            if not hasattr(client, "chat"):
                raise RuntimeError("Groq client unavailable")
            payload = _base_payload(configured=True, status="ready", model=model)
        except Exception:
            payload = _base_payload(configured=True, status="temporarily_unavailable", model=model)

    _CACHE["payload"] = payload
    _CACHE["expires_at"] = now + _CACHE_TTL_SECONDS
    return dict(payload)


def clear_groq_provider_cache() -> None:
    _CACHE["payload"] = None
    _CACHE["expires_at"] = 0.0
