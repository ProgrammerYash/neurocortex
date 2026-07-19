"""Central consent eligibility and event recording (Phase 3C / 3C.1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.consent_form_version import ConsentFormVersion
from app.models.daily_session import DailySession
from app.models.participant import Participant
from app.models.participant_consent_event import ParticipantConsentEvent
from app.models.study_protocol import StudyProtocol
from app.services.audit_service import record_audit_event
from app.services.study_guard import is_synthetic_public_id, should_filter_synthetic_data

VALID_CONSENT_CATEGORIES = frozenset({"under_18", "age_18_or_over", "unresolved"})
AMBIGUOUS_AGE_RANGES = frozenset({"17-18"})

ASSENT_EVENT_TYPES = frozenset({"assent_granted", "assent_declined"})
PARENTAL_EVENT_TYPES = frozenset({"parental_permission_granted", "parental_permission_declined"})
ADULT_EVENT_TYPES = frozenset({"adult_consent_granted", "adult_consent_declined"})
WITHDRAWAL_EVENT_TYPES = frozenset({"withdrawn", "reinstated"})
ML_EVENT_TYPES = frozenset({"excluded_from_ml", "included_in_ml"})
DELETION_EVENT_TYPES = frozenset({"deletion_requested"})
GRANTED_EVENT_TYPES = frozenset(
    {"assent_granted", "parental_permission_granted", "adult_consent_granted"}
)

SESSION_BLOCK_MESSAGES = {
    "CONSENT_REQUIRED": "Research consent has not been completed.",
    "PARENTAL_PERMISSION_REQUIRED": "Parental permission is pending verification by the research team.",
    "AGE_CONSENT_CATEGORY_REQUIRED": "Your age consent category must be resolved by the research team before sessions can begin.",
    "PARTICIPANT_WITHDRAWN": "You have withdrawn from the study.",
    "PROTOCOL_INACTIVE": "The active study protocol is not currently available for sessions.",
    "CONSENT_EXPIRED": "Consent has expired for the active protocol.",
}


def session_block_message(error_code: str | None) -> str | None:
    if not error_code:
        return None
    return SESSION_BLOCK_MESSAGES.get(error_code, "Session access is blocked by consent policy.")


class ConsentError(Exception):
    def __init__(self, message: str, *, status_code: int = 403, error_code: str = "CONSENT_REQUIRED"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def require_consent_for_sessions() -> bool:
    return get_settings().require_consent_for_sessions


def allow_researcher_consent_override() -> bool:
    return get_settings().allow_researcher_consent_override


def resolve_consent_category(participant: Participant) -> str:
    if participant.age_consent_category:
        return participant.age_consent_category
    age_range = participant.age_range.strip()
    if age_range in {"13-14", "15-16"}:
        return "under_18"
    if age_range in {"19-20", "21-22", "23+"}:
        return "age_18_or_over"
    return "unresolved"


def get_age_category(participant: Participant) -> str:
    category = resolve_consent_category(participant)
    if category == "under_18":
        return "minor"
    if category == "age_18_or_over":
        return "adult"
    return "unresolved"


def required_consent_types(participant: Participant) -> list[str]:
    category = resolve_consent_category(participant)
    if category == "under_18":
        return ["participant_assent", "parental_permission"]
    if category == "age_18_or_over":
        return ["adult_informed_consent"]
    return []


def validate_registration_consent_category(age_range: str, age_consent_category: str | None) -> str:
    normalized_range = age_range.strip()
    if age_consent_category:
        normalized = age_consent_category.strip()
        if normalized not in {"under_18", "age_18_or_over"}:
            raise ConsentError(
                "Invalid age consent category",
                status_code=422,
                error_code="INVALID_AGE_CONSENT_CATEGORY",
            )
        return normalized
    if normalized_range in AMBIGUOUS_AGE_RANGES:
        raise ConsentError(
            "Age consent category is required for the selected age range",
            status_code=422,
            error_code="AGE_CONSENT_CATEGORY_REQUIRED",
        )
    if normalized_range in {"13-14", "15-16"}:
        return "under_18"
    if normalized_range in {"19-20", "21-22", "23+"}:
        return "age_18_or_over"
    raise ConsentError(
        f"Unsupported age range '{age_range}'",
        status_code=422,
        error_code="INVALID_AGE_RANGE",
    )


def resolve_active_protocol(db: Session) -> StudyProtocol:
    version = get_settings().active_study_protocol_version.strip()
    protocol = db.execute(
        select(StudyProtocol).where(
            StudyProtocol.version == version,
            StudyProtocol.active.is_(True),
        )
    ).scalar_one_or_none()
    if protocol is None:
        protocol = db.execute(
            select(StudyProtocol)
            .where(StudyProtocol.active.is_(True))
            .order_by(StudyProtocol.effective_at.desc())
        ).scalar_one_or_none()
    if protocol is None:
        raise ConsentError("Active study protocol not configured", status_code=500, error_code="PROTOCOL_NOT_FOUND")
    return protocol


def configured_protocol_session_block(db: Session) -> str | None:
    if not require_consent_for_sessions():
        return None
    version = get_settings().active_study_protocol_version.strip()
    configured = db.execute(
        select(StudyProtocol).where(StudyProtocol.version == version)
    ).scalar_one_or_none()
    if configured is None or not configured.active:
        return "PROTOCOL_INACTIVE"
    return None


def _active_form_version(db: Session, *, protocol_id: UUID, form_type: str) -> ConsentFormVersion:
    form = db.execute(
        select(ConsentFormVersion)
        .where(
            ConsentFormVersion.protocol_id == protocol_id,
            ConsentFormVersion.form_type == form_type,
            ConsentFormVersion.active.is_(True),
        )
        .order_by(ConsentFormVersion.effective_at.desc())
    ).scalar_one_or_none()
    if form is None:
        raise ConsentError(
            f"No active consent form version configured for '{form_type}'",
            status_code=500,
            error_code="CONSENT_FORM_VERSION_MISSING",
        )
    if not form.active:
        raise ConsentError("Consent form version is inactive", error_code="CONSENT_FORM_VERSION_INACTIVE")
    return form


def _validate_granted_event(
    *,
    db: Session,
    protocol: StudyProtocol,
    event_type: str,
    status: str,
    consent_form_version_id: UUID | None,
    acknowledged_at: datetime | None,
) -> None:
    if status != "granted" or event_type not in GRANTED_EVENT_TYPES:
        return
    if consent_form_version_id is None:
        raise ConsentError(
            "Granted consent events must reference an active form version",
            status_code=422,
            error_code="CONSENT_FORM_VERSION_REQUIRED",
        )
    if acknowledged_at is None:
        raise ConsentError(
            "Granted consent events must include an acknowledgment timestamp",
            status_code=422,
            error_code="ACKNOWLEDGMENT_REQUIRED",
        )
    form = db.get(ConsentFormVersion, consent_form_version_id)
    if form is None:
        raise ConsentError("Consent form version not found", error_code="CONSENT_FORM_VERSION_INVALID")
    if not form.active:
        raise ConsentError("Consent form version is inactive", error_code="CONSENT_FORM_VERSION_INACTIVE")
    if form.protocol_id != protocol.id:
        raise ConsentError(
            "Consent form version belongs to another protocol",
            error_code="CONSENT_FORM_VERSION_INVALID",
        )
    if not protocol.active:
        raise ConsentError("Study protocol is inactive", error_code="PROTOCOL_INACTIVE")


def _load_consent_events(db: Session, *, participant_id: UUID, protocol_id: UUID) -> list[ParticipantConsentEvent]:
    return db.execute(
        select(ParticipantConsentEvent)
        .where(
            ParticipantConsentEvent.participant_id == participant_id,
            ParticipantConsentEvent.protocol_id == protocol_id,
        )
        .order_by(ParticipantConsentEvent.created_at.asc())
    ).scalars().all()


def _latest_status(events: list[ParticipantConsentEvent], event_types: frozenset[str]) -> str | None:
    for event in reversed(events):
        if event.event_type in event_types:
            return event.status
    return None


def _latest_event(events: list[ParticipantConsentEvent], event_types: frozenset[str]) -> ParticipantConsentEvent | None:
    for event in reversed(events):
        if event.event_type in event_types:
            return event
    return None


def _latest_status_before(
    events: list[ParticipantConsentEvent],
    event_types: frozenset[str],
    as_of: datetime,
) -> str | None:
    filtered = [event for event in events if event.created_at <= as_of]
    return _latest_status(filtered, event_types)


def consent_eligible_at_session_time(
    db: Session,
    participant: Participant,
    session: DailySession,
) -> tuple[bool, list[str]]:
    """Return eligibility and exclusion reasons for dataset building at session completion time."""
    reasons: list[str] = []
    as_of = session.completed_at or session.updated_at or session.started_at
    if as_of is None:
        reasons.append("SESSION_NOT_COMPLETED")
        return False, reasons

    if should_filter_synthetic_data() and is_synthetic_public_id(participant.public_id):
        reasons.append("SYNTHETIC_TEST_DATA")
        return False, reasons

    protocol = resolve_active_protocol(db)
    events = _load_consent_events(db, participant_id=participant.id, protocol_id=protocol.id)
    age_category = get_age_category(participant)
    consent_category = resolve_consent_category(participant)

    withdrawal_status = _latest_status_before(events, WITHDRAWAL_EVENT_TYPES, as_of) or "active"
    if withdrawal_status == "withdrawn":
        reasons.append("PARTICIPANT_WITHDRAWN_AT_SESSION_TIME")
        return False, reasons

    if consent_category == "unresolved" or age_category == "unresolved":
        reasons.append("AGE_CONSENT_CATEGORY_REQUIRED")
        return False, reasons

    assent_status = _latest_status_before(events, ASSENT_EVENT_TYPES, as_of) or "pending"
    parental_status = _latest_status_before(events, PARENTAL_EVENT_TYPES, as_of) or "pending"
    adult_status = _latest_status_before(events, ADULT_EVENT_TYPES, as_of) or "pending"

    if age_category == "minor":
        if assent_status != "granted":
            reasons.append("CONSENT_NOT_ACTIVE_AT_SESSION_TIME")
            return False, reasons
        if parental_status != "granted":
            reasons.append("PARENTAL_PERMISSION_NOT_ACTIVE_AT_SESSION_TIME")
            return False, reasons
    elif adult_status != "granted":
        reasons.append("CONSENT_NOT_ACTIVE_AT_SESSION_TIME")
        return False, reasons

    return True, reasons


def build_consent_status(db: Session, participant: Participant) -> dict[str, Any]:
    protocol = resolve_active_protocol(db)
    events = _load_consent_events(db, participant_id=participant.id, protocol_id=protocol.id)
    age_category = get_age_category(participant)
    consent_category = resolve_consent_category(participant)

    assent_status = _latest_status(events, ASSENT_EVENT_TYPES) or "pending"
    parental_status = _latest_status(events, PARENTAL_EVENT_TYPES) or "pending"
    adult_status = _latest_status(events, ADULT_EVENT_TYPES) or "pending"
    withdrawal_status = _latest_status(events, WITHDRAWAL_EVENT_TYPES) or "active"
    ml_excluded = _latest_event(events, ML_EVENT_TYPES)
    ml_excluded_flag = ml_excluded is not None and ml_excluded.event_type == "excluded_from_ml"
    deletion_requested = _latest_event(events, DELETION_EVENT_TYPES) is not None

    protocol_block = configured_protocol_session_block(db)
    session_eligible, session_block_reason = _session_eligibility_details(
        protocol_block=protocol_block,
        age_category=age_category,
        consent_category=consent_category,
        assent_status=assent_status,
        parental_status=parental_status,
        adult_status=adult_status,
        withdrawal_status=withdrawal_status,
    )
    ml_eligible, ml_block_reason = _ml_eligibility_details(
        participant=participant,
        age_category=age_category,
        consent_category=consent_category,
        assent_status=assent_status,
        parental_status=parental_status,
        adult_status=adult_status,
        withdrawal_status=withdrawal_status,
        ml_excluded=ml_excluded_flag,
        deletion_requested=deletion_requested,
    )

    return {
        "participant_id": participant.public_id,
        "age_range": participant.age_range,
        "age_consent_category": consent_category,
        "protocol_version": protocol.version,
        "age_category": age_category,
        "required_consent_types": required_consent_types(participant),
        "assent_status": assent_status if age_category == "minor" else "not_applicable",
        "parental_permission_status": parental_status if age_category == "minor" else "not_applicable",
        "adult_consent_status": adult_status if age_category == "adult" else "not_applicable",
        "withdrawal_status": withdrawal_status,
        "deletion_requested": deletion_requested,
        "excluded_from_ml": ml_excluded_flag,
        "session_eligible": session_eligible,
        "session_block_reason": session_block_reason,
        "session_block_message": session_block_message(session_block_reason) if not session_eligible else None,
        "ml_eligible": ml_eligible,
        "ml_block_reason": ml_block_reason,
        "require_consent_for_sessions": require_consent_for_sessions(),
    }


def _session_eligibility_details(
    *,
    protocol_block: str | None,
    age_category: str,
    consent_category: str,
    assent_status: str,
    parental_status: str,
    adult_status: str,
    withdrawal_status: str,
) -> tuple[bool, str | None]:
    if withdrawal_status == "withdrawn":
        return False, "PARTICIPANT_WITHDRAWN"
    if not require_consent_for_sessions():
        return True, None
    if protocol_block:
        return False, protocol_block
    if consent_category == "unresolved" or age_category == "unresolved":
        return False, "AGE_CONSENT_CATEGORY_REQUIRED"
    if age_category == "minor":
        if assent_status != "granted":
            return False, "CONSENT_REQUIRED"
        if parental_status != "granted":
            return False, "PARENTAL_PERMISSION_REQUIRED"
        return True, None
    if adult_status != "granted":
        return False, "CONSENT_REQUIRED"
    return True, None


def _ml_eligibility_details(
    *,
    participant: Participant,
    age_category: str,
    consent_category: str,
    assent_status: str,
    parental_status: str,
    adult_status: str,
    withdrawal_status: str,
    ml_excluded: bool,
    deletion_requested: bool,
) -> tuple[bool, str | None]:
    if should_filter_synthetic_data() and is_synthetic_public_id(participant.public_id):
        return False, "SYNTHETIC_TEST_DATA"
    if withdrawal_status == "withdrawn":
        return False, "PARTICIPANT_WITHDRAWN"
    if deletion_requested:
        return False, "DELETION_REQUESTED"
    if ml_excluded:
        return False, "EXCLUDED_FROM_ML"
    if consent_category == "unresolved" or age_category == "unresolved":
        return False, "AGE_CONSENT_CATEGORY_REQUIRED"
    if age_category == "minor":
        if assent_status != "granted" or parental_status != "granted":
            return False, "CONSENT_REQUIRED"
    elif adult_status != "granted":
        return False, "CONSENT_REQUIRED"
    return True, None


def assert_session_allowed(db: Session, participant: Participant) -> None:
    status = build_consent_status(db, participant)
    if status["session_eligible"]:
        return
    reason = status["session_block_reason"] or "CONSENT_REQUIRED"
    message = session_block_message(reason) or "Session access is blocked by consent policy"
    raise ConsentError(message, error_code=reason)


def is_ml_eligible(db: Session, participant: Participant) -> tuple[bool, str | None]:
    status = build_consent_status(db, participant)
    return status["ml_eligible"], status["ml_block_reason"]


def _append_event(
    db: Session,
    *,
    participant: Participant,
    protocol: StudyProtocol,
    event_type: str,
    status: str,
    recorded_by: str,
    consent_form_version_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
    acknowledged_at: datetime | None = None,
) -> ParticipantConsentEvent:
    _validate_granted_event(
        db=db,
        protocol=protocol,
        event_type=event_type,
        status=status,
        consent_form_version_id=consent_form_version_id,
        acknowledged_at=acknowledged_at,
    )
    event = ParticipantConsentEvent(
        id=uuid.uuid4(),
        participant_id=participant.id,
        protocol_id=protocol.id,
        consent_form_version_id=consent_form_version_id,
        event_type=event_type,
        status=status,
        recorded_by=recorded_by,
        acknowledged_at=acknowledged_at or datetime.now(UTC),
        metadata_json=metadata or {},
        created_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event


def record_participant_consent(
    db: Session,
    *,
    participant: Participant,
    payload: dict[str, Any],
) -> dict[str, Any]:
    protocol = resolve_active_protocol(db)
    age_category = get_age_category(participant)
    now = datetime.now(UTC)

    if age_category == "unresolved":
        raise ConsentError(
            "Age consent category must be resolved before recording consent",
            error_code="AGE_CONSENT_CATEGORY_REQUIRED",
            status_code=422,
        )

    if age_category == "minor":
        if payload.get("assent_acknowledged") is True:
            form = _active_form_version(db, protocol_id=protocol.id, form_type="participant_assent")
            _append_event(
                db,
                participant=participant,
                protocol=protocol,
                event_type="assent_granted",
                status="granted",
                recorded_by="participant_self",
                consent_form_version_id=form.id,
                metadata={"source": "enrollment_form"},
                acknowledged_at=now,
            )
        elif payload.get("assent_acknowledged") is False:
            _append_event(
                db,
                participant=participant,
                protocol=protocol,
                event_type="assent_declined",
                status="declined",
                recorded_by="participant_self",
                metadata={"source": "enrollment_form"},
                acknowledged_at=now,
            )

        parental_status = payload.get("parental_permission_status")
        if parental_status == "granted":
            raise ConsentError(
                "Participants cannot self-verify parental permission",
                status_code=422,
                error_code="PARENTAL_PERMISSION_SELF_VERIFY_DENIED",
            )
        if parental_status == "declined":
            _append_event(
                db,
                participant=participant,
                protocol=protocol,
                event_type="parental_permission_declined",
                status="declined",
                recorded_by="participant_self",
                metadata={"source": "enrollment_form", "verification": "participant_reported"},
                acknowledged_at=now,
            )
    else:
        if payload.get("adult_consent_acknowledged") is True:
            form = _active_form_version(db, protocol_id=protocol.id, form_type="adult_informed_consent")
            _append_event(
                db,
                participant=participant,
                protocol=protocol,
                event_type="adult_consent_granted",
                status="granted",
                recorded_by="participant_self",
                consent_form_version_id=form.id,
                metadata={"source": "enrollment_form"},
                acknowledged_at=now,
            )
        elif payload.get("adult_consent_acknowledged") is False:
            _append_event(
                db,
                participant=participant,
                protocol=protocol,
                event_type="adult_consent_declined",
                status="declined",
                recorded_by="participant_self",
                metadata={"source": "enrollment_form"},
                acknowledged_at=now,
            )

    record_audit_event(
        db,
        actor_type="participant",
        actor_id=participant.id,
        participant_id=participant.id,
        event_type="consent_recorded",
        metadata={"protocol_version": protocol.version},
    )
    db.commit()
    return build_consent_status(db, participant)


def record_withdrawal(db: Session, *, participant: Participant) -> dict[str, Any]:
    protocol = resolve_active_protocol(db)
    _append_event(
        db,
        participant=participant,
        protocol=protocol,
        event_type="withdrawn",
        status="withdrawn",
        recorded_by="participant_self",
        metadata={"source": "participant_withdrawal"},
    )
    record_audit_event(
        db,
        actor_type="participant",
        actor_id=participant.id,
        participant_id=participant.id,
        event_type="participant_withdrawn",
    )
    db.commit()
    return build_consent_status(db, participant)


def record_deletion_request(db: Session, *, participant: Participant) -> dict[str, Any]:
    protocol = resolve_active_protocol(db)
    _append_event(
        db,
        participant=participant,
        protocol=protocol,
        event_type="deletion_requested",
        status="pending",
        recorded_by="participant_self",
        metadata={"source": "participant_request"},
    )
    record_audit_event(
        db,
        actor_type="participant",
        actor_id=participant.id,
        participant_id=participant.id,
        event_type="deletion_requested",
    )
    db.commit()
    return build_consent_status(db, participant)


def record_researcher_consent_event(
    db: Session,
    *,
    participant: Participant,
    researcher_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not allow_researcher_consent_override():
        raise ConsentError(
            "Researcher consent override is disabled",
            status_code=403,
            error_code="OVERRIDE_DISABLED",
        )
    protocol = resolve_active_protocol(db)
    event_type = payload["event_type"]
    status = payload.get("status") or "granted"
    form_type = payload.get("form_type")
    if status == "granted" and event_type in GRANTED_EVENT_TYPES:
        if not form_type:
            raise ConsentError(
                "Granted researcher consent events require form_type",
                status_code=422,
                error_code="CONSENT_FORM_VERSION_REQUIRED",
            )
        form = _active_form_version(db, protocol_id=protocol.id, form_type=form_type)
    else:
        form = (
            _active_form_version(db, protocol_id=protocol.id, form_type=form_type)
            if form_type
            else None
        )
    acknowledged_at = payload.get("acknowledged_at")
    ack_dt = datetime.fromisoformat(acknowledged_at) if isinstance(acknowledged_at, str) else datetime.now(UTC)
    _append_event(
        db,
        participant=participant,
        protocol=protocol,
        event_type=event_type,
        status=status,
        recorded_by="researcher",
        consent_form_version_id=form.id if form else None,
        metadata={"source": "researcher_override", **(payload.get("metadata") or {})},
        acknowledged_at=ack_dt,
    )
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher_id,
        participant_id=participant.id,
        event_type="researcher_consent_override",
        metadata={"event_type": event_type, "status": status},
    )
    db.commit()
    return build_consent_status(db, participant)


def set_ml_exclusion(
    db: Session,
    *,
    participant: Participant,
    researcher_id: UUID,
    excluded: bool,
) -> dict[str, Any]:
    protocol = resolve_active_protocol(db)
    event_type = "excluded_from_ml" if excluded else "included_in_ml"
    status = "granted" if excluded else "pending"
    _append_event(
        db,
        participant=participant,
        protocol=protocol,
        event_type=event_type,
        status=status,
        recorded_by="researcher",
        metadata={"source": "researcher_ml_exclusion"},
    )
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher_id,
        participant_id=participant.id,
        event_type=event_type,
        metadata={"excluded": excluded},
    )
    db.commit()
    return build_consent_status(db, participant)


def resolve_participant_age_consent_category(
    db: Session,
    *,
    participant: Participant,
    researcher_id: UUID,
    age_consent_category: str,
) -> dict[str, Any]:
    current = resolve_consent_category(participant)
    if current != "unresolved":
        raise ConsentError(
            "Age consent category is already resolved",
            status_code=422,
            error_code="AGE_CONSENT_CATEGORY_ALREADY_RESOLVED",
        )
    normalized = age_consent_category.strip()
    if normalized not in {"under_18", "age_18_or_over"}:
        raise ConsentError(
            "Age consent category must be under_18 or age_18_or_over",
            status_code=422,
            error_code="INVALID_AGE_CONSENT_CATEGORY",
        )

    previous = participant.age_consent_category
    participant.age_consent_category = normalized
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher_id,
        participant_id=participant.id,
        event_type="age_consent_category_resolved",
        metadata={"previous": previous, "resolved_to": normalized},
    )
    db.commit()
    db.refresh(participant)
    return build_consent_status(db, participant)


def get_participant_by_public_id(db: Session, public_id: str) -> Participant:
    participant = db.execute(
        select(Participant).where(Participant.public_id == public_id.strip().upper())
    ).scalar_one_or_none()
    if participant is None:
        raise ConsentError("Participant not found", status_code=404, error_code="NOT_FOUND")
    return participant


def list_enrollment_statuses(db: Session) -> list[dict[str, Any]]:
    from app.services.study_guard import apply_participant_filter

    participants = db.execute(
        apply_participant_filter(select(Participant).order_by(Participant.created_at.asc()))
    ).scalars().all()
    return [build_consent_status(db, participant) for participant in participants]
