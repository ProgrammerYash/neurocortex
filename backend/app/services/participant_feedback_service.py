"""Participant-facing fixed-model feedback."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import DailySession
from app.models.participant import Participant
from app.services.fixed_model_service import FixedModelError, model_is_configured, run_fixed_model_inference
from app.services.ml_inference import extract_session_features
from app.services.participant_account_service import assert_login_allowed
from app.services.study_settings_service import get_study_settings


class ParticipantFeedbackError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _latest_completed_session(db: Session, participant_id: UUID) -> DailySession | None:
    return db.execute(
        select(DailySession)
        .options(selectinload(DailySession.module_results))
        .where(
            DailySession.participant_id == participant_id,
            DailySession.complete.is_(True),
        )
        .order_by(DailySession.session_date.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_participant_model_feedback(db: Session, participant: Participant) -> dict[str, object]:
    assert_login_allowed(participant)
    settings = get_study_settings(db)
    if not settings.participant_feedback_enabled:
        return {"status": "disabled"}

    if not model_is_configured():
        return {"status": "disabled"}

    session = _latest_completed_session(db, participant.id)
    if session is None:
        return {
            "status": "insufficient_data",
            "label": "Not enough data yet",
        }

    features, _flags = extract_session_features(participant=participant, session=session)
    try:
        _probability, category, label, model_version = run_fixed_model_inference(features)
    except FixedModelError:
        return {
            "status": "insufficient_data",
            "label": "Not enough data yet",
        }

    return {
        "status": "available",
        "category": category,
        "label": label,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
    }


def researcher_feedback_summary(db: Session) -> dict[str, object]:
    settings = get_study_settings(db)
    configured = model_is_configured()
    return {
        "participant_feedback_enabled": settings.participant_feedback_enabled,
        "participant_feedback_updated_at": settings.participant_feedback_updated_at,
        "model_configured": configured,
        "model_version": None if not configured else _safe_model_version(),
    }


def _safe_model_version() -> str | None:
    try:
        from app.services.fixed_model_service import load_manifest

        return str(load_manifest().get("model_version"))
    except FixedModelError:
        return None
