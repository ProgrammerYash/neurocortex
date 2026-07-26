"""Participant Groq feedback snapshots (release / revoke / participant view)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.participant import Participant
from app.models.participant_feedback_snapshot import ParticipantFeedbackSnapshot
from app.services.audit_service import record_audit_event
from contextlib import contextmanager

from app.services.feedback_generation_lock import (
    release_feedback_generation_lock,
    try_acquire_feedback_generation_lock,
)
from app.services.feedback_metrics_service import (
    build_deidentified_metric_summary,
    latest_completed_session_at,
    load_completed_sessions,
)
from app.services.groq_feedback_service import (
    FEEDBACK_WARNING,
    PROMPT_VERSION,
    GroqFeedbackError,
    generate_groq_feedback,
)
from app.services.groq_provider_service import get_groq_provider_status
from app.services.participant_account_service import assert_login_allowed

RESEARCHER_STATUS_NOT_RELEASED = "Not Released"
RESEARCHER_STATUS_RELEASED = "Released"
RESEARCHER_STATUS_INSUFFICIENT = "Insufficient Data"
RESEARCHER_STATUS_FAILED = "Generation Failed"
RESEARCHER_STATUS_REVOKED = "Revoked"


class ParticipantFeedbackError(Exception):
    def __init__(self, message: str, status_code: int = 400, *, error_code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def researcher_feedback_summary(db: Session) -> dict[str, Any]:
    provider = get_groq_provider_status()
    return {
        "groq_feedback_status": provider["status"],
        "groq_feedback_configured": provider["configured"],
        "groq_model": provider.get("model"),
    }


def _active_released_snapshot(db: Session, participant_id: UUID) -> ParticipantFeedbackSnapshot | None:
    return db.execute(
        select(ParticipantFeedbackSnapshot)
        .where(
            ParticipantFeedbackSnapshot.participant_id == participant_id,
            ParticipantFeedbackSnapshot.is_released.is_(True),
            ParticipantFeedbackSnapshot.revoked_at.is_(None),
        )
        .order_by(ParticipantFeedbackSnapshot.released_at.desc().nullslast())
        .limit(1)
    ).scalar_one_or_none()


def _latest_snapshot(db: Session, participant_id: UUID) -> ParticipantFeedbackSnapshot | None:
    return db.execute(
        select(ParticipantFeedbackSnapshot)
        .where(ParticipantFeedbackSnapshot.participant_id == participant_id)
        .order_by(ParticipantFeedbackSnapshot.generated_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def resolve_researcher_feedback_status(
    *,
    active: ParticipantFeedbackSnapshot | None,
    latest: ParticipantFeedbackSnapshot | None,
) -> str:
    if active is not None:
        if active.error_code:
            return RESEARCHER_STATUS_FAILED
        if active.status == "insufficient_data":
            return RESEARCHER_STATUS_INSUFFICIENT
        return RESEARCHER_STATUS_RELEASED
    if latest is not None:
        if latest.revoked_at is not None and latest.is_released is False:
            return RESEARCHER_STATUS_REVOKED
        if latest.error_code and not latest.is_released:
            return RESEARCHER_STATUS_FAILED
    return RESEARCHER_STATUS_NOT_RELEASED


def feedback_status_label(db: Session, participant_id: UUID) -> str:
    return resolve_researcher_feedback_status(
        active=_active_released_snapshot(db, participant_id),
        latest=_latest_snapshot(db, participant_id),
    )


def load_feedback_status_map(db: Session, participant_ids: list[UUID]) -> dict[UUID, str]:
    if not participant_ids:
        return {}
    active_rows = db.execute(
        select(ParticipantFeedbackSnapshot)
        .where(
            ParticipantFeedbackSnapshot.participant_id.in_(participant_ids),
            ParticipantFeedbackSnapshot.is_released.is_(True),
            ParticipantFeedbackSnapshot.revoked_at.is_(None),
        )
        .order_by(
            ParticipantFeedbackSnapshot.participant_id,
            ParticipantFeedbackSnapshot.released_at.desc().nullslast(),
        )
    ).scalars()
    active_by_participant: dict[UUID, ParticipantFeedbackSnapshot] = {}
    for row in active_rows:
        if row.participant_id not in active_by_participant:
            active_by_participant[row.participant_id] = row

    latest_subq = (
        select(
            ParticipantFeedbackSnapshot.participant_id,
            func.max(ParticipantFeedbackSnapshot.generated_at).label("max_generated"),
        )
        .where(ParticipantFeedbackSnapshot.participant_id.in_(participant_ids))
        .group_by(ParticipantFeedbackSnapshot.participant_id)
        .subquery()
    )
    latest_rows = db.execute(
        select(ParticipantFeedbackSnapshot).join(
            latest_subq,
            (ParticipantFeedbackSnapshot.participant_id == latest_subq.c.participant_id)
            & (ParticipantFeedbackSnapshot.generated_at == latest_subq.c.max_generated),
        )
    ).scalars()
    latest_by_participant = {row.participant_id: row for row in latest_rows}

    return {
        participant_id: resolve_researcher_feedback_status(
            active=active_by_participant.get(participant_id),
            latest=latest_by_participant.get(participant_id),
        )
        for participant_id in participant_ids
    }


def _unset_released(db: Session, participant_id: UUID, researcher_id: UUID | None) -> None:
    rows = db.execute(
        select(ParticipantFeedbackSnapshot).where(
            ParticipantFeedbackSnapshot.participant_id == participant_id,
            ParticipantFeedbackSnapshot.is_released.is_(True),
            ParticipantFeedbackSnapshot.revoked_at.is_(None),
        )
    ).scalars()
    now = datetime.now(UTC)
    for row in rows:
        row.is_released = False
        row.revoked_at = now
        row.revoked_by_researcher_id = researcher_id


def _persist_snapshot(
    db: Session,
    *,
    participant: Participant,
    researcher_id: UUID,
    parsed,
    request_id: str | None,
    metrics: dict[str, Any],
    sessions,
    model_name: str | None,
    release: bool,
    error_code: str | None = None,
) -> ParticipantFeedbackSnapshot:
    now = datetime.now(UTC)
    snapshot = ParticipantFeedbackSnapshot(
        participant_id=participant.id,
        status=parsed.status,
        level=parsed.level,
        headline=parsed.headline,
        summary=parsed.summary,
        factors=parsed.factors,
        provider="groq",
        provider_model=model_name,
        prompt_version=PROMPT_VERSION,
        generated_at=now,
        generated_by_researcher_id=researcher_id,
        source_session_count=metrics.get("completed_session_count", 0),
        source_latest_session_at=latest_completed_session_at(sessions),
        is_released=release,
        released_at=now if release else None,
        released_by_researcher_id=researcher_id if release else None,
        provider_request_id=request_id,
        error_code=error_code,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _record_generation_failure(
    db: Session,
    *,
    participant: Participant,
    researcher_id: UUID,
    metrics: dict[str, Any],
    sessions,
    model_name: str | None,
    error_code: str,
) -> None:
    from app.services.groq_feedback_service import GroqFeedbackModel

    parsed = GroqFeedbackModel(
        status="insufficient_data",
        level=None,
        headline="Feedback generation failed",
        summary="Feedback could not be generated at this time.",
        factors=[],
    )
    _persist_snapshot(
        db,
        participant=participant,
        researcher_id=researcher_id,
        parsed=parsed,
        request_id=None,
        metrics=metrics,
        sessions=sessions,
        model_name=model_name,
        release=False,
        error_code=error_code,
    )


@contextmanager
def _feedback_generation_lock(db: Session, participant_id: UUID):
    if not try_acquire_feedback_generation_lock(db, participant_id):
        raise ParticipantFeedbackError(
            "Feedback generation already in progress for this participant",
            status_code=409,
            error_code="GENERATION_IN_PROGRESS",
        )
    try:
        yield
    finally:
        release_feedback_generation_lock(db, participant_id)


def _generate_and_release(
    db: Session,
    *,
    participant: Participant,
    researcher_id: UUID,
    require_existing_release: bool,
) -> ParticipantFeedbackSnapshot:
    prior_released = _active_released_snapshot(db, participant.id)
    if require_existing_release and prior_released is None:
        raise ParticipantFeedbackError("No released feedback to refresh", status_code=422)

    metrics = build_deidentified_metric_summary(db, participant)
    sessions = load_completed_sessions(db, participant.id, limit=1)
    settings = get_groq_provider_status()
    model_name = settings.get("model")

    try:
        parsed, request_id = generate_groq_feedback(metrics)
    except GroqFeedbackError as exc:
        _record_generation_failure(
            db,
            participant=participant,
            researcher_id=researcher_id,
            metrics=metrics,
            sessions=sessions,
            model_name=model_name,
            error_code=exc.code,
        )
        record_audit_event(
            db,
            actor_type="researcher",
            actor_id=researcher_id,
            event_type="feedback.generation_failed",
            metadata={"participant_public_id": participant.public_id, "error_code": exc.code},
        )
        db.commit()
        raise ParticipantFeedbackError(exc.message, status_code=exc.status_code, error_code=exc.code) from exc

    _unset_released(db, participant.id, researcher_id)
    return _persist_snapshot(
        db,
        participant=participant,
        researcher_id=researcher_id,
        parsed=parsed,
        request_id=request_id,
        metrics=metrics,
        sessions=sessions,
        model_name=model_name,
        release=True,
    )


def release_participant_feedback(db: Session, *, participant: Participant, researcher_id: UUID) -> ParticipantFeedbackSnapshot:
    with _feedback_generation_lock(db, participant.id):
        snapshot = _generate_and_release(
            db,
            participant=participant,
            researcher_id=researcher_id,
            require_existing_release=False,
        )
        record_audit_event(
            db,
            actor_type="researcher",
            actor_id=researcher_id,
            event_type="feedback.released",
            metadata={"participant_public_id": participant.public_id, "snapshot_id": str(snapshot.id)},
        )
        db.commit()
        db.refresh(snapshot)
        return snapshot


def refresh_participant_feedback(db: Session, *, participant: Participant, researcher_id: UUID) -> ParticipantFeedbackSnapshot:
    with _feedback_generation_lock(db, participant.id):
        snapshot = _generate_and_release(
            db,
            participant=participant,
            researcher_id=researcher_id,
            require_existing_release=True,
        )
        record_audit_event(
            db,
            actor_type="researcher",
            actor_id=researcher_id,
            event_type="feedback.refreshed",
            metadata={"participant_public_id": participant.public_id, "snapshot_id": str(snapshot.id)},
        )
        db.commit()
        db.refresh(snapshot)
        return snapshot


def revoke_participant_feedback(db: Session, *, participant: Participant, researcher_id: UUID) -> None:
    _unset_released(db, participant.id, researcher_id)
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher_id,
        event_type="feedback.revoked",
        metadata={"participant_public_id": participant.public_id},
    )
    db.commit()


def get_participant_model_feedback(db: Session, participant: Participant) -> dict[str, object]:
    assert_login_allowed(participant)
    snapshot = _active_released_snapshot(db, participant.id)
    if snapshot is None:
        return {"status": "not_released"}

    if snapshot.status == "insufficient_data":
        return {
            "status": "insufficient_data",
            "label": "Not enough data yet",
            "headline": snapshot.headline,
            "summary": snapshot.summary or "Complete at least one full study session before feedback can be generated.",
            "warning": FEEDBACK_WARNING,
        }

    if snapshot.error_code:
        return {"status": "not_released"}

    return {
        "status": "available",
        "level": snapshot.level,
        "headline": snapshot.headline,
        "summary": snapshot.summary,
        "factors": snapshot.factors or [],
        "generated_at": snapshot.generated_at.isoformat(),
        "source_session_count": snapshot.source_session_count,
        "warning": FEEDBACK_WARNING,
    }
