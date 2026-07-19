"""Versioned study procedure configuration and session protocol enforcement."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.daily_session import (
    ACTIVE_SESSION_STATUSES,
    SESSION_STATUS_ABANDONED,
    SESSION_STATUS_COMPLETE,
    SESSION_STATUS_INCOMPLETE,
    SESSION_STATUS_IN_PROGRESS,
    DailySession,
)
from app.models.study_procedure import StudyProcedureVersion
from app.models.study_protocol import StudyProtocol
from app.services.consent_service import resolve_active_protocol

PROCEDURE_BLOCK_MESSAGES = {
    "STUDY_NOT_STARTED": "The study has not started yet.",
    "STUDY_ENDED": "The study enrollment period has ended.",
    "DAILY_SESSION_LIMIT_REACHED": "You have reached the maximum number of sessions allowed for today.",
    "SESSION_INTERVAL_TOO_SOON": "Please wait before starting another session.",
    "MODULE_ORDER_VIOLATION": "Complete the previous modules before starting this one.",
    "MODULE_SKIP_NOT_ALLOWED": "Required modules cannot be skipped.",
    "SESSION_ALREADY_COMPLETE": "Today's session is already complete.",
    "SESSION_ABANDONED": "This session was abandoned. Start a new session when eligible.",
    "PROCEDURE_INACTIVE": "The active study procedure is not currently available.",
}


def procedure_block_message(error_code: str | None) -> str | None:
    if not error_code:
        return None
    return PROCEDURE_BLOCK_MESSAGES.get(error_code, "Session access is blocked by study procedure policy.")


class ProcedureError(Exception):
    def __init__(self, message: str, *, status_code: int = 403, error_code: str = "PROCEDURE_BLOCKED"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def serialize_procedure(procedure: StudyProcedureVersion) -> dict[str, Any]:
    return {
        "version": procedure.version,
        "active": procedure.active,
        "required_modules": list(procedure.required_modules or []),
        "required_survey_questions": list(procedure.required_survey_questions or []),
        "min_session_duration_seconds": procedure.min_session_duration_seconds,
        "max_session_duration_seconds": procedure.max_session_duration_seconds,
        "max_sessions_per_day": procedure.max_sessions_per_day,
        "min_minutes_between_sessions": procedure.min_minutes_between_sessions,
        "study_start_date": procedure.study_start_date.isoformat(),
        "study_end_date": procedure.study_end_date.isoformat(),
        "participant_target": procedure.participant_target,
        "min_sessions_per_participant": procedure.min_sessions_per_participant,
        "effective_at": procedure.effective_at.isoformat(),
    }


def resolve_active_procedure(db: Session) -> StudyProcedureVersion:
    version = get_settings().active_study_procedure_version.strip()
    procedure = db.execute(
        select(StudyProcedureVersion).where(
            StudyProcedureVersion.version == version,
            StudyProcedureVersion.active.is_(True),
        )
    ).scalar_one_or_none()
    if procedure is None:
        protocol = resolve_active_protocol(db)
        procedure = db.execute(
            select(StudyProcedureVersion)
            .where(
                StudyProcedureVersion.protocol_id == protocol.id,
                StudyProcedureVersion.active.is_(True),
            )
            .order_by(StudyProcedureVersion.effective_at.desc())
        ).scalar_one_or_none()
    if procedure is None:
        raise ProcedureError(
            "Active study procedure not configured",
            status_code=500,
            error_code="PROCEDURE_NOT_FOUND",
        )
    return procedure


def get_active_procedure_for_researcher(db: Session) -> dict[str, Any]:
    procedure = resolve_active_procedure(db)
    protocol = db.get(StudyProtocol, procedure.protocol_id)
    payload = serialize_procedure(procedure)
    payload["protocol_version"] = protocol.version if protocol else None
    return payload


def _sessions_on_date(db: Session, *, participant_id: UUID, session_date: date) -> list[DailySession]:
    return db.execute(
        select(DailySession)
        .options(selectinload(DailySession.module_results))
        .where(
            DailySession.participant_id == participant_id,
            DailySession.session_date == session_date,
        )
        .order_by(DailySession.session_slot.asc())
    ).scalars().all()


def _last_completed_session(db: Session, *, participant_id: UUID) -> DailySession | None:
    return db.execute(
        select(DailySession)
        .where(
            DailySession.participant_id == participant_id,
            DailySession.status == SESSION_STATUS_COMPLETE,
        )
        .order_by(DailySession.completed_at.desc().nullslast(), DailySession.updated_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _assert_study_dates(procedure: StudyProcedureVersion, session_date: date) -> None:
    if session_date < procedure.study_start_date:
        raise ProcedureError(
            procedure_block_message("STUDY_NOT_STARTED") or "Study not started",
            error_code="STUDY_NOT_STARTED",
        )
    if session_date > procedure.study_end_date:
        raise ProcedureError(
            procedure_block_message("STUDY_ENDED") or "Study ended",
            error_code="STUDY_ENDED",
        )


def _next_eligible_at(db: Session, *, participant_id: UUID, procedure: StudyProcedureVersion) -> datetime | None:
    last_completed = _last_completed_session(db, participant_id=participant_id)
    if last_completed is None or last_completed.completed_at is None:
        return None
    return last_completed.completed_at + timedelta(minutes=procedure.min_minutes_between_sessions)


def assert_can_start_or_continue_session(
    db: Session,
    *,
    participant_id: UUID,
    session_date: date,
    procedure: StudyProcedureVersion,
    existing_session: DailySession | None,
) -> None:
    _assert_study_dates(procedure, session_date)

    if existing_session is not None:
        if existing_session.status == SESSION_STATUS_ABANDONED:
            raise ProcedureError(
                procedure_block_message("SESSION_ABANDONED") or "Session abandoned",
                error_code="SESSION_ABANDONED",
            )
        if existing_session.status == SESSION_STATUS_COMPLETE:
            raise ProcedureError(
                procedure_block_message("SESSION_ALREADY_COMPLETE") or "Session complete",
                error_code="SESSION_ALREADY_COMPLETE",
            )
        return

    sessions_today = [
        session
        for session in _sessions_on_date(db, participant_id=participant_id, session_date=session_date)
        if session.status in ACTIVE_SESSION_STATUSES
    ]
    if len(sessions_today) >= procedure.max_sessions_per_day:
        raise ProcedureError(
            procedure_block_message("DAILY_SESSION_LIMIT_REACHED") or "Daily limit reached",
            error_code="DAILY_SESSION_LIMIT_REACHED",
        )

    next_eligible = _next_eligible_at(db, participant_id=participant_id, procedure=procedure)
    if next_eligible is not None and datetime.now(UTC) < next_eligible:
        raise ProcedureError(
            procedure_block_message("SESSION_INTERVAL_TOO_SOON") or "Interval too soon",
            error_code="SESSION_INTERVAL_TOO_SOON",
        )


def assert_module_order(
    session: DailySession,
    *,
    module_key: str,
    procedure: StudyProcedureVersion,
) -> None:
    required = list(procedure.required_modules or [])
    if module_key not in required:
        return

    present = {result.module_key for result in session.module_results}
    if module_key in present:
        return

    target_index = required.index(module_key)
    missing_before = [key for key in required[:target_index] if key not in present]
    if missing_before:
        raise ProcedureError(
            procedure_block_message("MODULE_ORDER_VIOLATION") or "Module order violation",
            error_code="MODULE_ORDER_VIOLATION",
            status_code=422,
        )


def get_or_create_working_session(
    db: Session,
    *,
    participant_id: UUID,
    session_date: date,
    procedure: StudyProcedureVersion,
) -> DailySession:
    sessions = _sessions_on_date(db, participant_id=participant_id, session_date=session_date)
    for session in sessions:
        if session.status == SESSION_STATUS_IN_PROGRESS:
            assert_can_start_or_continue_session(
                db,
                participant_id=participant_id,
                session_date=session_date,
                procedure=procedure,
                existing_session=session,
            )
            return session

    assert_can_start_or_continue_session(
        db,
        participant_id=participant_id,
        session_date=session_date,
        procedure=procedure,
        existing_session=None,
    )

    next_slot = max((session.session_slot for session in sessions), default=-1) + 1
    now = datetime.now(UTC)
    session = DailySession(
        participant_id=participant_id,
        session_date=session_date,
        session_slot=next_slot,
        status=SESSION_STATUS_IN_PROGRESS,
        complete=False,
        started_at=now,
        procedure_version=procedure.version,
    )
    db.add(session)
    db.flush()
    return session


def recompute_session_completion(session: DailySession, procedure: StudyProcedureVersion) -> None:
    required = set(procedure.required_modules or [])
    present = {result.module_key for result in session.module_results}
    session.complete = required.issubset(present)
    if session.complete and session.status == SESSION_STATUS_IN_PROGRESS:
        session.status = SESSION_STATUS_COMPLETE
        session.completed_at = datetime.now(UTC)
    elif not session.complete and session.status == SESSION_STATUS_COMPLETE:
        session.status = SESSION_STATUS_IN_PROGRESS
        session.completed_at = None


def mark_session_abandoned(db: Session, session: DailySession) -> DailySession:
    if session.status == SESSION_STATUS_COMPLETE:
        raise ProcedureError(
            "Completed sessions cannot be abandoned",
            error_code="SESSION_ALREADY_COMPLETE",
            status_code=409,
        )
    now = datetime.now(UTC)
    session.status = SESSION_STATUS_ABANDONED
    session.abandoned_at = now
    session.complete = False
    session.completed_at = None
    session.updated_at = now
    db.commit()
    db.refresh(session)
    return session


def mark_session_incomplete(db: Session, session: DailySession) -> DailySession:
    if session.status == SESSION_STATUS_COMPLETE:
        raise ProcedureError(
            "Completed sessions cannot be marked incomplete",
            error_code="SESSION_ALREADY_COMPLETE",
            status_code=409,
        )
    session.status = SESSION_STATUS_INCOMPLETE
    session.complete = False
    session.completed_at = None
    session.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(session)
    return session


def count_completed_sessions(db: Session, *, participant_id: UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(DailySession)
        .where(
            DailySession.participant_id == participant_id,
            DailySession.status == SESSION_STATUS_COMPLETE,
        )
    ).scalar_one()


def build_participant_study_progress(
    db: Session,
    *,
    participant_id: UUID,
    session_date: date,
    consent_eligible: bool,
    consent_block_reason: str | None,
    consent_block_message: str | None,
    withdrawal_status: str,
) -> dict[str, Any]:
    procedure = resolve_active_procedure(db)
    completed = count_completed_sessions(db, participant_id=participant_id)
    required = procedure.min_sessions_per_participant

    today_sessions = _sessions_on_date(db, participant_id=participant_id, session_date=session_date)
    today_complete = any(session.status == SESSION_STATUS_COMPLETE for session in today_sessions)
    in_progress = next(
        (session for session in today_sessions if session.status == SESSION_STATUS_IN_PROGRESS),
        None,
    )

    next_eligible = _next_eligible_at(db, participant_id=participant_id, procedure=procedure)
    session_can_start = consent_eligible
    block_reason = consent_block_reason
    block_message = consent_block_message

    if session_can_start:
        try:
            assert_can_start_or_continue_session(
                db,
                participant_id=participant_id,
                session_date=session_date,
                procedure=procedure,
                existing_session=in_progress,
            )
        except ProcedureError as exc:
            session_can_start = False
            block_reason = exc.error_code
            block_message = procedure_block_message(exc.error_code)

    if withdrawal_status == "withdrawn":
        study_status = "withdrawn"
    elif session_date > procedure.study_end_date:
        study_status = "study_ended"
    elif completed >= required:
        study_status = "completed"
    elif completed > 0 or today_complete or in_progress is not None:
        study_status = "in_progress"
    elif session_date < procedure.study_start_date:
        study_status = "not_started"
    else:
        study_status = "in_progress"

    return {
        "procedure_version": procedure.version,
        "completed_sessions": completed,
        "required_sessions": required,
        "next_eligible_session_at": next_eligible.isoformat() if next_eligible else None,
        "study_status": study_status,
        "today_session_complete": today_complete,
        "session_can_start": session_can_start,
        "session_block_reason": block_reason,
        "session_block_message": block_message,
        "study_start_date": procedure.study_start_date.isoformat(),
        "study_end_date": procedure.study_end_date.isoformat(),
    }
