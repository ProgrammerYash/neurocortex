"""Generate structured participant feedback via Groq."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import get_settings

PROMPT_VERSION = "2026-07-v1"
FEEDBACK_WARNING = (
    "NeuroCortex can make mistakes and should not be fully relied on. "
    "This is an AI-generated research estimate, not a medical or psychological diagnosis."
)

GROQ_FEEDBACK_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "neurocortex_feedback",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["available", "insufficient_data"],
                },
                "level": {
                    "type": "string",
                    "enum": ["low", "moderate", "elevated", "unclear"],
                },
                "headline": {
                    "type": "string",
                    "maxLength": 80,
                },
                "summary": {
                    "type": "string",
                    "maxLength": 500,
                },
                "factors": {
                    "type": "array",
                    "maxItems": 3,
                    "items": {
                        "type": "string",
                        "maxLength": 120,
                    },
                },
            },
            "required": ["status", "level", "headline", "summary", "factors"],
            "additionalProperties": False,
        },
    },
}

SYSTEM_PROMPT = """You analyze de-identified study metrics for a youth research program.
Return JSON that conforms exactly to the enforced response schema.
status must be exactly one of: available, insufficient_data
level must be exactly one of: low, moderate, elevated, unclear
headline must be at most 80 characters.
summary must be at most 500 characters.
factors must contain at most 3 short strings.
Provide non-diagnostic research feedback.
Do not claim a medical or psychological condition.
Do not provide treatment or emergency advice.
Do not mention training data or claim certainty.
Use calm, age-appropriate language.
If metrics are too sparse, use status insufficient_data with neutral headline and summary.
"""


class GroqFeedbackModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "insufficient_data"]
    level: Literal["low", "moderate", "elevated", "unclear"] | None = None
    headline: str = Field(max_length=80)
    summary: str = Field(max_length=500)
    factors: list[str] = Field(default_factory=list, max_length=3)

    @field_validator("factors")
    @classmethod
    def trim_factors(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values if isinstance(item, str) and item.strip()]
        return cleaned[:3]


class GroqFeedbackError(Exception):
    def __init__(self, message: str, *, code: str = "GROQ_ERROR", status_code: int = 502):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def _parse_response_content(content: str) -> GroqFeedbackModel:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise GroqFeedbackError("Groq returned invalid JSON", code="INVALID_JSON") from exc
    try:
        return GroqFeedbackModel.model_validate(payload)
    except Exception as exc:
        raise GroqFeedbackError("Groq JSON failed validation", code="SCHEMA_MISMATCH") from exc


def _exception_code(exc: Exception) -> str:
    text = str(exc).lower()
    if "429" in str(exc) or "rate limit" in text or "rate_limit" in text:
        return "RATE_LIMIT"
    if "401" in str(exc) or "403" in str(exc) or "authentication" in text or "invalid api key" in text:
        return "AUTH_FAILURE"
    return "PROVIDER_FAILURE"


def _should_retry(exc: Exception, *, attempt: int, max_attempts: int) -> bool:
    if attempt >= max_attempts - 1:
        return False
    code = _exception_code(exc)
    if code in {"AUTH_FAILURE", "RATE_LIMIT"}:
        return False
    if isinstance(exc, GroqFeedbackError):
        return exc.code in {"PROVIDER_FAILURE", "INVALID_JSON", "SCHEMA_MISMATCH"}
    return True


def generate_groq_feedback(metrics: dict[str, Any]) -> tuple[GroqFeedbackModel, str | None]:
    if metrics.get("completed_session_count", 0) < 1:
        return (
            GroqFeedbackModel(
                status="insufficient_data",
                level=None,
                headline="Not enough data yet",
                summary="Complete at least one full study session before feedback can be generated.",
                factors=[],
            ),
            None,
        )

    settings = get_settings()
    api_key = (settings.groq_api_key or "").strip()
    model = (settings.groq_model or "").strip()
    if not api_key or not model:
        raise GroqFeedbackError("Groq is not configured", code="NOT_CONFIGURED", status_code=503)

    from groq import Groq

    client = Groq(api_key=api_key, timeout=settings.groq_timeout_seconds)
    user_payload = json.dumps({"metrics": metrics}, ensure_ascii=True)
    last_error: Exception | None = None
    request_id: str | None = None
    max_attempts = max(1, settings.groq_max_retries + 1)
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Analyze these de-identified metrics. "
                            "Return JSON with status, level, headline, summary, factors only.\n"
                            f"{user_payload}"
                        ),
                    },
                ],
                response_format=GROQ_FEEDBACK_RESPONSE_FORMAT,
                temperature=0.2,
                stream=False,
            )
            request_id = getattr(response, "id", None)
            content = response.choices[0].message.content or ""
            return _parse_response_content(content), request_id
        except GroqFeedbackError:
            raise
        except Exception as exc:
            last_error = exc
            code = _exception_code(exc)
            if code == "RATE_LIMIT":
                raise GroqFeedbackError("Groq rate limit exceeded", code="RATE_LIMIT", status_code=429) from exc
            if code == "AUTH_FAILURE":
                raise GroqFeedbackError("Groq authentication failed", code="AUTH_FAILURE", status_code=401) from exc
            if not _should_retry(exc, attempt=attempt, max_attempts=max_attempts):
                break
            continue
    raise GroqFeedbackError("Groq request failed", code="PROVIDER_FAILURE") from last_error
