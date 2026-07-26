"""Database-enforced lock to prevent concurrent feedback generation per participant."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.participant_feedback_generation_lock import ParticipantFeedbackGenerationLock

LOCK_TTL = timedelta(minutes=5)


def _purge_expired_locks(db: Session) -> None:
    now = datetime.now(UTC)
    db.execute(delete(ParticipantFeedbackGenerationLock).where(ParticipantFeedbackGenerationLock.expires_at < now))


def try_acquire_feedback_generation_lock(db: Session, participant_id: UUID) -> bool:
    _purge_expired_locks(db)
    now = datetime.now(UTC)
    try:
        with db.begin_nested():
            lock = ParticipantFeedbackGenerationLock(
                participant_id=participant_id,
                locked_at=now,
                expires_at=now + LOCK_TTL,
            )
            db.add(lock)
            db.flush()
        return True
    except IntegrityError:
        return False


def release_feedback_generation_lock(db: Session, participant_id: UUID) -> None:
    db.execute(
        delete(ParticipantFeedbackGenerationLock).where(
            ParticipantFeedbackGenerationLock.participant_id == participant_id
        )
    )
    db.flush()


def feedback_generation_in_progress(db: Session, participant_id: UUID) -> bool:
    _purge_expired_locks(db)
    row = db.execute(
        select(ParticipantFeedbackGenerationLock).where(
            ParticipantFeedbackGenerationLock.participant_id == participant_id
        )
    ).scalar_one_or_none()
    return row is not None
