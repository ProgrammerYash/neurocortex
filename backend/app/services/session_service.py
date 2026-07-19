from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import DailySession
from app.models.module_result import ModuleResult
from app.models.participant import Participant
from app.services.data_quality_service import record_module_resubmission_flag, validate_session_data_quality
from app.services.procedure_service import (
    ProcedureError,
    assert_module_order,
    get_or_create_working_session,
    mark_session_abandoned,
    procedure_block_message,
    recompute_session_completion,
    resolve_active_procedure,
)


class SessionError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str | None = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def serialize_session(session: DailySession, public_id: str) -> dict[str, object]:
    record: dict[str, object] = {
        "date": session.session_date.isoformat(),
        "sessionId": f"{public_id}_{session.session_date.isoformat()}_{session.session_slot}",
        "sessionSlot": session.session_slot,
        "status": session.status,
        "complete": session.complete,
        "startedAt": session.started_at.isoformat() if session.started_at else None,
        "completedAt": session.completed_at.isoformat() if session.completed_at else None,
        "abandonedAt": session.abandoned_at.isoformat() if session.abandoned_at else None,
        "procedureVersion": session.procedure_version,
    }
    for module_result in session.module_results:
        record[module_result.module_key] = module_result.payload
    return record


def list_participant_sessions(db: Session, participant: Participant) -> list[dict[str, object]]:
    sessions = db.execute(
        select(DailySession)
        .options(selectinload(DailySession.module_results))
        .where(DailySession.participant_id == participant.id)
        .order_by(DailySession.session_date.asc(), DailySession.session_slot.asc())
    ).scalars().all()
    return [serialize_session(session, participant.public_id) for session in sessions]


def get_participant_session_for_date(
    db: Session,
    participant: Participant,
    session_date: date,
    *,
    session_slot: int | None = None,
) -> DailySession | None:
    query = (
        select(DailySession)
        .options(selectinload(DailySession.module_results))
        .where(
            DailySession.participant_id == participant.id,
            DailySession.session_date == session_date,
        )
    )
    if session_slot is not None:
        query = query.where(DailySession.session_slot == session_slot)
    sessions = db.execute(query.order_by(DailySession.session_slot.asc())).scalars().all()
    if session_slot is not None:
        return sessions[0] if sessions else None
    in_progress = next((session for session in sessions if session.status == "in_progress"), None)
    if in_progress is not None:
        return in_progress
    return sessions[-1] if sessions else None


def today_session_date() -> date:
    """Match frontend dateToday() which uses UTC ISO date."""
    return datetime.now(UTC).date()


def get_today_session(db: Session, participant: Participant) -> dict[str, object] | None:
    session = get_participant_session_for_date(db, participant, today_session_date())
    if session is None:
        return None
    return serialize_session(session, participant.public_id)


def recompute_complete(db: Session, session: DailySession) -> None:
    procedure = resolve_active_procedure(db)
    recompute_session_completion(session, procedure)


def upsert_module_result(
    db: Session,
    participant: Participant,
    session_date: date,
    module_key: str,
    payload: dict[str, object],
) -> dict[str, object]:
    from app.services.consent_service import ConsentError, assert_session_allowed

    try:
        assert_session_allowed(db, participant)
    except ConsentError as exc:
        raise SessionError(exc.message, status_code=exc.status_code, error_code=exc.error_code) from exc

    if module_key not in VALID_MODULE_KEYS:
        raise SessionError(
            f"module_key must be one of: {', '.join(sorted(VALID_MODULE_KEYS))}",
            status_code=400,
        )
    if not payload:
        raise SessionError("payload must not be empty", status_code=400)

    procedure = resolve_active_procedure(db)
    try:
        session = get_or_create_working_session(
            db,
            participant_id=participant.id,
            session_date=session_date,
            procedure=procedure,
        )
        assert_module_order(session, module_key=module_key, procedure=procedure)
    except ProcedureError as exc:
        raise SessionError(
            exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
        ) from exc

    module_result = db.execute(
        select(ModuleResult).where(
            ModuleResult.session_id == session.id,
            ModuleResult.module_key == module_key,
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    is_resubmission = module_result is not None
    if module_result is None:
        module_result = ModuleResult(
            session_id=session.id,
            module_key=module_key,
            payload=payload,
            recorded_at=now,
        )
        db.add(module_result)
    else:
        module_result.payload = payload
        module_result.recorded_at = now
        record_module_resubmission_flag(db, session_id=session.id, module_key=module_key)

    db.flush()
    db.refresh(session, attribute_names=["module_results"])
    recompute_session_completion(session, procedure)
    validate_session_data_quality(db, session)
    session.updated_at = now
    db.commit()
    db.refresh(session)
    db.refresh(session, attribute_names=["module_results"])
    return serialize_session(session, participant.public_id)


def abandon_session(
    db: Session,
    participant: Participant,
    session_date: date,
) -> dict[str, object]:
    from app.services.consent_service import ConsentError, assert_session_allowed

    try:
        assert_session_allowed(db, participant)
    except ConsentError as exc:
        raise SessionError(exc.message, status_code=exc.status_code, error_code=exc.error_code) from exc

    session = get_participant_session_for_date(db, participant, session_date)
    if session is None:
        raise SessionError("No session found for this date", status_code=404, error_code="SESSION_NOT_FOUND")
    try:
        mark_session_abandoned(db, session)
    except ProcedureError as exc:
        raise SessionError(exc.message, status_code=exc.status_code, error_code=exc.error_code) from exc
    return serialize_session(session, participant.public_id)


# Imported after class definitions to avoid circular imports at module load.
from app.schemas.session import VALID_MODULE_KEYS  # noqa: E402
