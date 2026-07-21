"""Researcher participant account management and participant auth enforcement."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.participant import Participant
from app.models.participant_account_action import ParticipantAccountAction
from app.models.researcher import Researcher
from app.utils.security import hash_pin

STUDY_TIMEZONE = ZoneInfo("America/New_York")

SUSPEND_DURATION_CODES = frozenset(
    {"24_hours", "48_hours", "1_week", "1_month", "indefinite"}
)
SUSPEND_DURATION_DELTAS: dict[str, timedelta | None] = {
    "24_hours": timedelta(hours=24),
    "48_hours": timedelta(hours=48),
    "1_week": timedelta(days=7),
    "1_month": timedelta(days=30),
    "indefinite": None,
}

ACTION_SUSPEND_PREFIX = "suspend_"
ACTION_TYPES = frozenset(
    {
        "suspend_24_hours",
        "suspend_48_hours",
        "suspend_1_week",
        "suspend_1_month",
        "suspend_indefinitely",
        "unsuspend",
        "reset_pin",
        "disable",
        "enable",
        "remove_account_access",
    }
)

STATUS_REMOVED = "Removed"
STATUS_DISABLED = "Disabled"
STATUS_SUSPENDED = "Suspended"
STATUS_WITHDRAWN = "Withdrawn"
STATUS_ACTIVE = "Active"
STATUS_INACTIVE = "Inactive"


class AccountError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        error_code: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.extra = extra or {}
        super().__init__(message)


def format_study_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    local = value.astimezone(STUDY_TIMEZONE)
    return local.strftime("%b %d, %Y %I:%M %p").lstrip("0").replace(" 0", " ")


def _now() -> datetime:
    return datetime.now(UTC)


def _snapshot_state(participant: Participant) -> dict[str, Any]:
    return {
        "is_suspended": participant.is_suspended,
        "suspended_at": participant.suspended_at.isoformat() if participant.suspended_at else None,
        "suspended_until": participant.suspended_until.isoformat() if participant.suspended_until else None,
        "suspension_reason": participant.suspension_reason,
        "is_disabled": participant.is_disabled,
        "disabled_at": participant.disabled_at.isoformat() if participant.disabled_at else None,
        "disabled_reason": participant.disabled_reason,
        "removed_at": participant.removed_at.isoformat() if participant.removed_at else None,
        "removal_reason": participant.removal_reason,
        "must_change_pin": participant.must_change_pin,
        "auth_version": participant.auth_version,
    }


def clear_expired_suspension(participant: Participant, *, db: Session | None = None) -> bool:
    if not participant.is_suspended:
        return False
    if participant.suspended_until is None:
        return False
    now = _now()
    until = participant.suspended_until
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    if until > now:
        return False
    participant.is_suspended = False
    participant.suspended_at = None
    participant.suspended_until = None
    participant.suspension_reason = None
    if db is not None:
        db.flush()
    return True


def is_effectively_suspended(participant: Participant) -> bool:
    if not participant.is_suspended:
        return False
    if participant.suspended_until is None:
        return True
    until = participant.suspended_until
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    return until > _now()


def resolve_display_status(
    participant: Participant,
    *,
    withdrawal_status: str | None,
    last_active_at: datetime | None,
    sessions_started: int,
) -> str:
    clear_expired_suspension(participant)
    if participant.removed_at is not None:
        return STATUS_REMOVED
    if participant.is_disabled:
        return STATUS_DISABLED
    if is_effectively_suspended(participant):
        return STATUS_SUSPENDED
    if withdrawal_status == "withdrawn":
        return STATUS_WITHDRAWN
    if last_active_at is not None:
        now = _now()
        if last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=UTC)
        if now - last_active_at <= timedelta(days=7):
            return STATUS_ACTIVE
    if sessions_started > 0:
        return STATUS_INACTIVE
    return STATUS_INACTIVE


def account_state_payload(participant: Participant) -> dict[str, Any]:
    clear_expired_suspension(participant)
    suspended = is_effectively_suspended(participant)
    return {
        "isSuspended": suspended,
        "suspendedAt": participant.suspended_at,
        "suspendedUntil": participant.suspended_until if suspended else None,
        "suspensionReason": participant.suspension_reason if suspended else None,
        "suspendedUntilDisplay": format_study_datetime(participant.suspended_until) if suspended else None,
        "isDisabled": participant.is_disabled,
        "disabledAt": participant.disabled_at,
        "disabledReason": participant.disabled_reason if participant.is_disabled else None,
        "isRemoved": participant.removed_at is not None,
        "removedAt": participant.removed_at,
        "removalReason": participant.removal_reason if participant.removed_at else None,
        "mustChangePin": participant.must_change_pin,
    }


def assert_login_allowed(participant: Participant) -> None:
    clear_expired_suspension(participant)
    if participant.removed_at is not None:
        raise AccountError(
            "This account is no longer active.",
            status_code=401,
            error_code="ACCOUNT_REMOVED",
        )
    if participant.is_disabled:
        raise AccountError(
            "Your account has been disabled. Contact the study researcher.",
            status_code=401,
            error_code="ACCOUNT_DISABLED",
        )
    if is_effectively_suspended(participant):
        extra: dict[str, Any] = {"suspension_reason": participant.suspension_reason}
        if participant.suspended_until is not None:
            extra["suspended_until"] = participant.suspended_until.isoformat()
        message = (
            f"Your account is temporarily suspended until {format_study_datetime(participant.suspended_until)}."
            if participant.suspended_until
            else "Your account is suspended indefinitely."
        )
        raise AccountError(message, status_code=401, error_code="ACCOUNT_SUSPENDED", extra=extra)


def assert_token_valid(participant: Participant, token_auth_version: int | None) -> None:
    if token_auth_version is None or token_auth_version != participant.auth_version:
        raise AccountError(
            "Your session is no longer valid. Please sign in again.",
            status_code=401,
            error_code="TOKEN_REVOKED",
        )


def assert_participant_access(
    participant: Participant,
    *,
    token_auth_version: int | None,
    allow_pin_change_only: bool = False,
) -> None:
    assert_token_valid(participant, token_auth_version)
    clear_expired_suspension(participant)
    if participant.must_change_pin and not allow_pin_change_only:
        raise AccountError(
            "Your PIN was reset. Create a new PIN to continue.",
            status_code=403,
            error_code="PIN_CHANGE_REQUIRED",
        )
    if participant.removed_at is not None:
        raise AccountError(
            "This account is no longer active.",
            status_code=403,
            error_code="ACCOUNT_REMOVED",
        )
    if participant.is_disabled:
        raise AccountError(
            "Your account has been disabled. Contact the study researcher.",
            status_code=403,
            error_code="ACCOUNT_DISABLED",
        )
    if is_effectively_suspended(participant):
        extra: dict[str, Any] = {"suspension_reason": participant.suspension_reason}
        if participant.suspended_until is not None:
            extra["suspended_until"] = participant.suspended_until.isoformat()
        message = (
            f"Your account is temporarily suspended until {format_study_datetime(participant.suspended_until)}."
            if participant.suspended_until
            else "Your account is suspended indefinitely."
        )
        raise AccountError(message, status_code=403, error_code="ACCOUNT_SUSPENDED", extra=extra)


def increment_auth_version(participant: Participant) -> None:
    participant.auth_version = int(participant.auth_version or 0) + 1


def generate_temporary_pin() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"


def _validate_reason(reason: str) -> str:
    cleaned = reason.strip()
    if len(cleaned) < 3:
        raise AccountError("A reason of at least 3 characters is required.")
    return cleaned


def _get_participant_by_public_id(db: Session, public_id: str) -> Participant:
    participant = db.execute(
        select(Participant).where(Participant.public_id == public_id)
    ).scalar_one_or_none()
    if participant is None:
        raise AccountError("Participant not found", status_code=404, error_code="PARTICIPANT_NOT_FOUND")
    return participant


def _recent_duplicate(
    db: Session,
    *,
    participant_id: UUID,
    action_type: str,
    window_seconds: int = 3,
) -> ParticipantAccountAction | None:
    cutoff = _now() - timedelta(seconds=window_seconds)
    return db.execute(
        select(ParticipantAccountAction)
        .where(
            ParticipantAccountAction.participant_id == participant_id,
            ParticipantAccountAction.action_type == action_type,
            ParticipantAccountAction.created_at >= cutoff,
        )
        .order_by(ParticipantAccountAction.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _record_action(
    db: Session,
    *,
    participant: Participant,
    researcher: Researcher,
    action_type: str,
    reason: str,
    duration_code: str | None = None,
    previous_state: dict[str, Any],
    resulting_state: dict[str, Any],
) -> ParticipantAccountAction:
    duplicate = _recent_duplicate(db, participant_id=participant.id, action_type=action_type)
    if duplicate is not None:
        return duplicate
    action = ParticipantAccountAction(
        participant_id=participant.id,
        researcher_id=researcher.id,
        action_type=action_type,
        reason=reason,
        duration_code=duration_code,
        previous_state=previous_state,
        resulting_state=resulting_state,
    )
    db.add(action)
    db.flush()
    return action


def suspend_participant(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
    duration: str,
    reason: str,
) -> dict[str, Any]:
    if duration not in SUSPEND_DURATION_CODES:
        raise AccountError("Invalid suspension duration.")
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise AccountError("Removed accounts cannot be suspended.", status_code=409)
    cleaned_reason = _validate_reason(reason)
    previous = _snapshot_state(participant)
    now = _now()
    delta = SUSPEND_DURATION_DELTAS[duration]
    participant.is_suspended = True
    participant.suspended_at = now
    participant.suspended_until = now + delta if delta is not None else None
    participant.suspension_reason = cleaned_reason
    increment_auth_version(participant)
    action_type = f"suspend_{duration}" if duration != "indefinite" else "suspend_indefinitely"
    _record_action(
        db,
        participant=participant,
        researcher=researcher,
        action_type=action_type,
        reason=cleaned_reason,
        duration_code=duration,
        previous_state=previous,
        resulting_state=_snapshot_state(participant),
    )
    db.commit()
    db.refresh(participant)
    return _action_response(participant, action_type)


def unsuspend_participant(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
    reason: str,
) -> dict[str, Any]:
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise AccountError("Removed accounts cannot be unsuspended.", status_code=409)
    if not is_effectively_suspended(participant):
        raise AccountError("Participant is not currently suspended.", status_code=409)
    cleaned_reason = _validate_reason(reason)
    previous = _snapshot_state(participant)
    participant.is_suspended = False
    participant.suspended_at = None
    participant.suspended_until = None
    participant.suspension_reason = None
    increment_auth_version(participant)
    _record_action(
        db,
        participant=participant,
        researcher=researcher,
        action_type="unsuspend",
        reason=cleaned_reason,
        previous_state=previous,
        resulting_state=_snapshot_state(participant),
    )
    db.commit()
    db.refresh(participant)
    return _action_response(participant, "unsuspend")


def disable_participant(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
    reason: str,
) -> dict[str, Any]:
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise AccountError("Removed accounts cannot be disabled.", status_code=409)
    cleaned_reason = _validate_reason(reason)
    previous = _snapshot_state(participant)
    now = _now()
    participant.is_disabled = True
    participant.disabled_at = now
    participant.disabled_reason = cleaned_reason
    increment_auth_version(participant)
    _record_action(
        db,
        participant=participant,
        researcher=researcher,
        action_type="disable",
        reason=cleaned_reason,
        previous_state=previous,
        resulting_state=_snapshot_state(participant),
    )
    db.commit()
    db.refresh(participant)
    return _action_response(participant, "disable")


def enable_participant(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
    reason: str,
) -> dict[str, Any]:
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise AccountError("Removed accounts cannot be re-enabled.", status_code=409)
    if not participant.is_disabled:
        raise AccountError("Participant is not disabled.", status_code=409)
    cleaned_reason = _validate_reason(reason)
    previous = _snapshot_state(participant)
    participant.is_disabled = False
    participant.disabled_at = None
    participant.disabled_reason = None
    increment_auth_version(participant)
    _record_action(
        db,
        participant=participant,
        researcher=researcher,
        action_type="enable",
        reason=cleaned_reason,
        previous_state=previous,
        resulting_state=_snapshot_state(participant),
    )
    db.commit()
    db.refresh(participant)
    return _action_response(participant, "enable")


def remove_participant_access(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
    reason: str,
    confirmation_public_id: str,
) -> dict[str, Any]:
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise AccountError("Account access has already been removed.", status_code=409)
    cleaned_reason = _validate_reason(reason)
    confirmed = confirmation_public_id.strip().upper()
    if confirmed != participant.public_id:
        raise AccountError(
            "Confirmation participant ID does not match.",
            error_code="CONFIRMATION_MISMATCH",
        )
    previous = _snapshot_state(participant)
    now = _now()
    participant.removed_at = now
    participant.removal_reason = cleaned_reason
    participant.is_disabled = False
    participant.disabled_at = None
    participant.disabled_reason = None
    participant.is_suspended = False
    participant.suspended_at = None
    participant.suspended_until = None
    participant.suspension_reason = None
    participant.must_change_pin = False
    participant.pin_hash = hash_pin(secrets.token_hex(32))
    increment_auth_version(participant)
    _record_action(
        db,
        participant=participant,
        researcher=researcher,
        action_type="remove_account_access",
        reason=cleaned_reason,
        previous_state=previous,
        resulting_state=_snapshot_state(participant),
    )
    db.commit()
    db.refresh(participant)
    return _action_response(participant, "remove_account_access")


def reset_participant_pin(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
) -> dict[str, Any]:
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise AccountError("Removed accounts cannot have PINs reset.", status_code=409)
    previous = _snapshot_state(participant)
    temporary_pin = generate_temporary_pin()
    participant.pin_hash = hash_pin(temporary_pin)
    participant.must_change_pin = True
    increment_auth_version(participant)
    _record_action(
        db,
        participant=participant,
        researcher=researcher,
        action_type="reset_pin",
        reason="PIN reset by researcher",
        previous_state=previous,
        resulting_state=_snapshot_state(participant),
    )
    db.commit()
    db.refresh(participant)
    response = _action_response(participant, "reset_pin")
    response["temporaryPin"] = temporary_pin
    return response


def change_participant_pin(
    db: Session,
    *,
    participant: Participant,
    new_pin: str,
    pin_confirmation: str,
) -> dict[str, Any]:
    if participant.removed_at is not None:
        raise AccountError("This account is no longer active.", error_code="ACCOUNT_REMOVED")
    if not participant.must_change_pin:
        raise AccountError("PIN change is not required.", status_code=409)
    if new_pin != pin_confirmation:
        raise AccountError("PIN confirmation does not match.")
    if not new_pin.isdigit() or not 4 <= len(new_pin) <= 6:
        raise AccountError("PIN must be 4–6 digits.")
    participant.pin_hash = hash_pin(new_pin)
    participant.must_change_pin = False
    increment_auth_version(participant)
    db.commit()
    db.refresh(participant)
    return {"must_change_pin": False, "auth_version": participant.auth_version}


def _action_response(participant: Participant, action_type: str) -> dict[str, Any]:
    return {
        "actionType": action_type,
        "participantId": participant.public_id,
        "authVersion": participant.auth_version,
        **account_state_payload(participant),
    }


def list_account_actions(db: Session, *, public_id: str, limit: int = 50) -> list[dict[str, Any]]:
    participant = _get_participant_by_public_id(db, public_id)
    actions = db.execute(
        select(ParticipantAccountAction)
        .options(selectinload(ParticipantAccountAction.researcher))
        .where(ParticipantAccountAction.participant_id == participant.id)
        .order_by(
            ParticipantAccountAction.created_at.desc(),
            ParticipantAccountAction.id.desc(),
        )
        .limit(limit)
    ).scalars().all()
    rows = []
    for action in actions:
        rows.append(
            {
                "id": str(action.id),
                "actionType": action.action_type,
                "reason": action.reason,
                "durationCode": action.duration_code,
                "researcherDisplayName": action.researcher.display_name if action.researcher else None,
                "createdAt": action.created_at,
                "createdAtDisplay": format_study_datetime(action.created_at),
                "previousState": action.previous_state,
                "resultingState": action.resulting_state,
            }
        )
    return rows


def matches_status_filter(display_status: str, status_filter: str | None) -> bool:
    if not status_filter or status_filter == "all_current":
        return display_status != STATUS_REMOVED
    normalized = status_filter.strip().lower()
    mapping = {
        "active": STATUS_ACTIVE,
        "inactive": STATUS_INACTIVE,
        "suspended": STATUS_SUSPENDED,
        "disabled": STATUS_DISABLED,
        "withdrawn": STATUS_WITHDRAWN,
        "removed": STATUS_REMOVED,
    }
    expected = mapping.get(normalized)
    if expected is None:
        return display_status != STATUS_REMOVED
    return display_status == expected
