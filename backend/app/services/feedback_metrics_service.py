"""De-identified participant metrics for Groq feedback."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import SESSION_STATUS_COMPLETE, DailySession
from app.models.module_result import ModuleResult
from app.models.participant import Participant
from app.schemas.session import CORE_MODULE_KEYS


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, 4)


def _module_payload(session: DailySession, key: str) -> dict[str, Any]:
    for result in session.module_results:
        if result.module_key == key:
            return dict(result.payload or {})
    return {}


def _session_metrics(session: DailySession, *, days_ago: int) -> dict[str, Any]:
    reaction = _module_payload(session, "reaction")
    typing = _module_payload(session, "typing")
    memory = _module_payload(session, "memory")
    attention = _module_payload(session, "attention")
    survey = _module_payload(session, "survey")
    metrics: dict[str, Any] = {
        "days_ago": days_ago,
        "session_date": session.session_date.isoformat(),
    }
    for key, payload in (
        ("reaction_avg_ms", reaction.get("avg")),
        ("reaction_sd_ms", reaction.get("sd")),
        ("typing_wpm", typing.get("wpm")),
        ("typing_error_rate", typing.get("errorRate")),
        ("memory_accuracy_pct", memory.get("accuracy")),
        ("attention_accuracy_pct", attention.get("accuracy")),
        ("survey_stress", survey.get("stress")),
        ("survey_fatigue", survey.get("fatigue")),
        ("survey_sleep_hours", survey.get("sleep")),
    ):
        cleaned = _safe_float(payload)
        if cleaned is not None:
            metrics[key] = cleaned
    return metrics


def load_completed_sessions(db: Session, participant_id, *, limit: int = 14) -> list[DailySession]:
    return db.execute(
        select(DailySession)
        .options(selectinload(DailySession.module_results))
        .where(
            DailySession.participant_id == participant_id,
            DailySession.status == SESSION_STATUS_COMPLETE,
        )
        .order_by(DailySession.session_date.desc(), DailySession.session_slot.desc())
        .limit(limit)
    ).scalars().all()


def build_deidentified_metric_summary(db: Session, participant: Participant) -> dict[str, Any]:
    sessions = load_completed_sessions(db, participant.id)
    if not sessions:
        return {"completed_session_count": 0, "sessions": []}
    latest_date = sessions[0].session_date
    session_rows = []
    for session in sessions:
        days_ago = (latest_date - session.session_date).days
        session_rows.append(_session_metrics(session, days_ago=days_ago))
    latest = sessions[0]
    present = {result.module_key for result in latest.module_results}
    missing_modules = [key for key in CORE_MODULE_KEYS if key not in present]
    return {
        "completed_session_count": len(sessions),
        "latest_session_date": latest_date.isoformat(),
        "sessions": session_rows,
        "notes": {
            "missing_latest_modules": missing_modules,
        },
    }


def latest_completed_session_at(sessions: list[DailySession]) -> datetime | None:
    if not sessions:
        return None
    session = sessions[0]
    return datetime.combine(session.session_date, datetime.min.time(), tzinfo=UTC)
