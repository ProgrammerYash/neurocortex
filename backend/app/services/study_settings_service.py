from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.study_settings import StudySettings
from app.services.audit_service import record_audit_event


class StudySettingsError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def get_study_settings(db: Session) -> StudySettings:
    settings = db.get(StudySettings, 1)
    if settings is None:
        settings = StudySettings(id=1, participant_feedback_enabled=False)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_participant_feedback_enabled(
    db: Session,
    *,
    enabled: bool,
    researcher_id: UUID,
) -> StudySettings:
    settings = get_study_settings(db)
    settings.participant_feedback_enabled = enabled
    settings.participant_feedback_updated_at = datetime.now(timezone.utc)
    settings.participant_feedback_updated_by = researcher_id
    db.add(settings)
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher_id,
        event_type="study_settings.participant_feedback_updated",
        metadata={"participant_feedback_enabled": enabled},
    )
    db.commit()
    db.refresh(settings)
    return settings
