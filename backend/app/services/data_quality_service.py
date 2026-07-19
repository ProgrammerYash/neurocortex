"""Automated session data-quality validation and researcher review workflow."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import (
    SESSION_STATUS_ABANDONED,
    SESSION_STATUS_COMPLETE,
    SESSION_STATUS_INCOMPLETE,
    SESSION_STATUS_IN_PROGRESS,
    DailySession,
)
from app.models.participant import Participant
from app.models.session_data_quality_flag import SessionDataQualityFlag
from app.services.audit_service import record_audit_event
from app.services.procedure_service import resolve_active_procedure

VALID_REVIEW_STATUSES = frozenset({"unresolved", "reviewed_valid", "reviewed_exclude"})
CRITICAL_FLAG_TYPES = frozenset(
    {
        "impossible_reaction_time",
        "empty_typing_sample",
        "missing_survey_values",
        "duplicate_module_submission",
        "session_too_fast",
        "too_many_missing_values",
    }
)

MIN_TYPING_TOTAL_KEYS = 20
IMPOSSIBLE_REACTION_MS = 80
SESSION_TOO_FAST_BUFFER_SECONDS = 5


class DataQualityError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _existing_flag_types(db: Session, session_id: UUID) -> set[str]:
    rows = db.execute(
        select(SessionDataQualityFlag.flag_type).where(SessionDataQualityFlag.session_id == session_id)
    ).scalars().all()
    return set(rows)


def _add_flag(
    db: Session,
    *,
    session_id: UUID,
    flag_type: str,
    severity: str,
    reason: str,
    module_key: str | None = None,
) -> SessionDataQualityFlag | None:
    existing = _existing_flag_types(db, session_id)
    if flag_type in existing:
        return None
    flag = SessionDataQualityFlag(
        session_id=session_id,
        module_key=module_key,
        flag_type=flag_type,
        severity=severity,
        reason=reason,
        review_status="unresolved",
    )
    db.add(flag)
    return flag


def validate_session_data_quality(db: Session, session: DailySession) -> list[SessionDataQualityFlag]:
    procedure = resolve_active_procedure(db)
    payloads = {result.module_key: result.payload for result in session.module_results}
    created: list[SessionDataQualityFlag] = []

    reaction = payloads.get("reaction") or {}
    if "reaction" in payloads:
        for field in ("min", "avg", "median"):
            value = reaction.get(field)
            if value is not None:
                try:
                    if float(value) < IMPOSSIBLE_REACTION_MS:
                        flag = _add_flag(
                            db,
                            session_id=session.id,
                            flag_type="impossible_reaction_time",
                            severity="critical",
                            reason=f"Reaction time field '{field}' is below {IMPOSSIBLE_REACTION_MS} ms",
                            module_key="reaction",
                        )
                        if flag:
                            created.append(flag)
                        break
                except (TypeError, ValueError):
                    pass

    typing = payloads.get("typing") or {}
    if "typing" in payloads:
        total_keys = typing.get("totalKeys")
        sample_text = typing.get("sampleText") or typing.get("text") or ""
        if not typing or (total_keys in (None, 0, "0") and not str(sample_text).strip()):
            flag = _add_flag(
                db,
                session_id=session.id,
                flag_type="empty_typing_sample",
                severity="critical",
                reason="Typing module payload is empty or contains no keystrokes",
                module_key="typing",
            )
            if flag:
                created.append(flag)
        else:
            try:
                keys = int(total_keys or 0)
            except (TypeError, ValueError):
                keys = 0
            if keys < MIN_TYPING_TOTAL_KEYS:
                flag = _add_flag(
                    db,
                    session_id=session.id,
                    flag_type="extremely_short_typing_sample",
                    severity="non_critical",
                    reason=f"Typing sample contains only {keys} keystrokes (minimum expected {MIN_TYPING_TOTAL_KEYS})",
                    module_key="typing",
                )
                if flag:
                    created.append(flag)

    survey = payloads.get("survey") or {}
    required_questions = list(procedure.required_survey_questions or [])
    if "survey" in payloads:
        missing_survey = [question for question in required_questions if survey.get(question) in (None, "")]
        if missing_survey:
            flag = _add_flag(
                db,
                session_id=session.id,
                flag_type="missing_survey_values",
                severity="critical",
                reason=f"Missing required survey fields: {', '.join(missing_survey)}",
                module_key="survey",
            )
            if flag:
                created.append(flag)

    if session.started_at and session.completed_at and session.status == SESSION_STATUS_COMPLETE:
        duration = (session.completed_at - session.started_at).total_seconds()
        if duration < max(procedure.min_session_duration_seconds - SESSION_TOO_FAST_BUFFER_SECONDS, 0):
            flag = _add_flag(
                db,
                session_id=session.id,
                flag_type="session_too_fast",
                severity="critical",
                reason=(
                    f"Session completed in {duration:.1f}s, below minimum "
                    f"{procedure.min_session_duration_seconds}s"
                ),
            )
            if flag:
                created.append(flag)
        if duration > procedure.max_session_duration_seconds:
            flag = _add_flag(
                db,
                session_id=session.id,
                flag_type="invalid_module_timing",
                severity="non_critical",
                reason=(
                    f"Session duration {duration:.1f}s exceeds configured maximum "
                    f"{procedure.max_session_duration_seconds}s"
                ),
            )
            if flag:
                created.append(flag)

    required_modules = set(procedure.required_modules or [])
    present_modules = set(payloads.keys())
    missing_modules = sorted(required_modules - present_modules)
    if session.status == SESSION_STATUS_COMPLETE and len(missing_modules) >= 2:
        flag = _add_flag(
            db,
            session_id=session.id,
            flag_type="too_many_missing_values",
            severity="critical",
            reason=f"Missing required modules: {', '.join(missing_modules)}",
        )
        if flag:
            created.append(flag)

    db.flush()
    return created


def record_module_resubmission_flag(db: Session, *, session_id: UUID, module_key: str) -> None:
    _add_flag(
        db,
        session_id=session_id,
        flag_type="duplicate_module_submission",
        severity="critical",
        reason=f"Module '{module_key}' was resubmitted after an earlier submission",
        module_key=module_key,
    )


def session_has_unresolved_critical_flags(db: Session, session_id: UUID) -> bool:
    count = db.execute(
        select(func.count())
        .select_from(SessionDataQualityFlag)
        .where(
            SessionDataQualityFlag.session_id == session_id,
            SessionDataQualityFlag.severity == "critical",
            SessionDataQualityFlag.review_status == "unresolved",
        )
    ).scalar_one()
    return count > 0


def session_has_reviewed_exclude(db: Session, session_id: UUID) -> bool:
    count = db.execute(
        select(func.count())
        .select_from(SessionDataQualityFlag)
        .where(
            SessionDataQualityFlag.session_id == session_id,
            SessionDataQualityFlag.review_status == "reviewed_exclude",
        )
    ).scalar_one()
    return count > 0


def review_data_quality_flag(
    db: Session,
    *,
    flag_id: UUID,
    researcher_id: UUID,
    review_status: str,
) -> SessionDataQualityFlag:
    if review_status not in VALID_REVIEW_STATUSES:
        raise DataQualityError(f"review_status must be one of: {', '.join(sorted(VALID_REVIEW_STATUSES))}")

    flag = db.get(SessionDataQualityFlag, flag_id)
    if flag is None:
        raise DataQualityError("Data quality flag not found", status_code=404)

    previous = flag.review_status
    flag.review_status = review_status
    flag.reviewed_by_researcher_id = researcher_id
    flag.reviewed_at = datetime.now(UTC)
    db.flush()

    record_audit_event(
        db,
        event_type="data_quality_flag_reviewed",
        actor_type="researcher",
        actor_id=researcher_id,
        metadata={
            "flag_id": str(flag.id),
            "session_id": str(flag.session_id),
            "flag_type": flag.flag_type,
            "previous_review_status": previous,
            "review_status": review_status,
        },
    )
    db.commit()
    db.refresh(flag)
    return flag


def serialize_flag(flag: SessionDataQualityFlag) -> dict[str, Any]:
    return {
        "id": str(flag.id),
        "session_id": str(flag.session_id),
        "module_key": flag.module_key,
        "flag_type": flag.flag_type,
        "severity": flag.severity,
        "reason": flag.reason,
        "review_status": flag.review_status,
        "reviewed_by_researcher_id": str(flag.reviewed_by_researcher_id) if flag.reviewed_by_researcher_id else None,
        "reviewed_at": flag.reviewed_at.isoformat() if flag.reviewed_at else None,
        "created_at": flag.created_at.isoformat(),
    }


def build_data_quality_dashboard(db: Session) -> dict[str, Any]:
    sessions = db.execute(
        select(DailySession).options(
            selectinload(DailySession.participant),
            selectinload(DailySession.data_quality_flags),
        )
    ).scalars().all()

    completed = sum(1 for session in sessions if session.status == SESSION_STATUS_COMPLETE)
    incomplete = sum(1 for session in sessions if session.status == SESSION_STATUS_INCOMPLETE)
    abandoned = sum(1 for session in sessions if session.status == SESSION_STATUS_ABANDONED)
    in_progress = sum(1 for session in sessions if session.status == SESSION_STATUS_IN_PROGRESS)

    flags = db.execute(select(SessionDataQualityFlag)).scalars().all()
    flagged_session_ids = {flag.session_id for flag in flags}
    flags_by_type: dict[str, int] = {}
    for flag in flags:
        flags_by_type[flag.flag_type] = flags_by_type.get(flag.flag_type, 0) + 1

    procedure = resolve_active_procedure(db)
    participants = db.execute(
        select(Participant).options(
            selectinload(Participant.daily_sessions).selectinload(DailySession.data_quality_flags)
        )
    ).scalars().all()
    below_minimum: list[dict[str, Any]] = []
    suspicious: list[dict[str, Any]] = []

    for participant in participants:
        completed_count = sum(
            1
            for session in participant.daily_sessions
            if session.status == SESSION_STATUS_COMPLETE
        )
        if completed_count < procedure.min_sessions_per_participant:
            below_minimum.append(
                {
                    "public_id": participant.public_id,
                    "completed_sessions": completed_count,
                    "required_sessions": procedure.min_sessions_per_participant,
                }
            )

        participant_flags = [
            flag
            for session in participant.daily_sessions
            for flag in session.data_quality_flags
            if flag.severity == "critical"
        ]
        if len(participant_flags) >= 3:
            suspicious.append(
                {
                    "public_id": participant.public_id,
                    "critical_flag_count": len(participant_flags),
                    "unresolved_critical_flag_count": sum(
                        1 for flag in participant_flags if flag.review_status == "unresolved"
                    ),
                }
            )

    return {
        "completed_sessions": completed,
        "incomplete_sessions": incomplete,
        "abandoned_sessions": abandoned,
        "in_progress_sessions": in_progress,
        "flagged_sessions": len(flagged_session_ids),
        "flags_by_type": flags_by_type,
        "participants_below_minimum_sessions": below_minimum,
        "participants_with_repeated_suspicious_results": suspicious,
        "total_flags": len(flags),
        "unresolved_critical_flags": sum(
            1 for flag in flags if flag.severity == "critical" and flag.review_status == "unresolved"
        ),
    }


def list_flagged_sessions(db: Session, *, limit: int = 100) -> list[dict[str, Any]]:
    flags = db.execute(
        select(SessionDataQualityFlag)
        .options(
            selectinload(SessionDataQualityFlag.session).selectinload(DailySession.participant),
        )
        .order_by(SessionDataQualityFlag.created_at.desc())
        .limit(limit)
    ).scalars().all()

    grouped: dict[UUID, dict[str, Any]] = {}
    for flag in flags:
        bucket = grouped.setdefault(
            flag.session_id,
            {
                "session_id": str(flag.session_id),
                "public_id": flag.session.participant.public_id if flag.session.participant else None,
                "session_date": flag.session.session_date.isoformat() if flag.session else None,
                "session_status": flag.session.status if flag.session else None,
                "flags": [],
            },
        )
        bucket["flags"].append(serialize_flag(flag))
    return list(grouped.values())
