"""Researcher bulk participant actions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.participant import Participant
from app.models.researcher import Researcher
from app.services.audit_service import record_audit_event
from app.services.participant_account_service import (
    AccountError,
    disable_participant,
    enable_participant,
    remove_participant_access,
    suspend_participant,
    unsuspend_participant,
)
from app.services.participant_feedback_service import (
    ParticipantFeedbackError,
    refresh_participant_feedback,
    release_participant_feedback,
    revoke_participant_feedback,
)
from app.services.participant_message_service import MessageError, send_participant_message
from app.services.researcher_dashboard_service import list_dashboard_participants
from app.services.smtp_email_service import email_is_configured, send_bulk_email
from app.services.study_guard import apply_participant_filter


MAX_BULK_IDS = 25


class BulkActionError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _resolve_public_ids(
    db: Session,
    *,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
) -> list[str]:
    excluded = {value.strip().upper() for value in (excluded_public_ids or []) if value}
    if selection_mode == "all_matching":
        filter_payload = filters or {}
        items, _total = list_dashboard_participants(
            db,
            limit=500,
            offset=0,
            search=filter_payload.get("search"),
            sort=filter_payload.get("sort") or "joined",
            direction=filter_payload.get("direction") or "desc",
            status_filter=filter_payload.get("status") or "all_current",
            participant_type_filter=filter_payload.get("participantType")
            or filter_payload.get("participant_type")
            or "all",
            include_participant_type=True,
        )
        ids = [row["participantId"] for row in items if row["participantId"] not in excluded]
        return ids[:500]
    ids = []
    for value in participant_public_ids or []:
        pid = value.strip().upper()
        if pid and pid not in excluded:
            ids.append(pid)
    return ids[:500]


def _participants_by_public_ids(db: Session, public_ids: list[str]) -> list[Participant]:
    if not public_ids:
        return []
    return db.execute(
        apply_participant_filter(select(Participant).where(Participant.public_id.in_(public_ids)))
    ).scalars().all()


def _result_shell(requested: list[str]) -> dict[str, Any]:
    return {
        "requested_count": len(requested),
        "eligible_count": 0,
        "succeeded_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "failures": [],
    }


def bulk_message(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
    subject: str,
    body: str,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    result = _result_shell(ids)
    for public_id in ids:
        result["eligible_count"] += 1
        try:
            send_participant_message(db, public_id=public_id, researcher=researcher, subject=subject, body=body)
            result["succeeded_count"] += 1
        except MessageError as exc:
            result["failed_count"] += 1
            result["failures"].append({"public_id": public_id, "message": exc.message})
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        event_type="bulk.message",
        metadata={"requested": result["requested_count"], "succeeded": result["succeeded_count"]},
    )
    return result


def bulk_release_feedback(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    participants = _participants_by_public_ids(db, ids)
    by_id = {participant.public_id: participant for participant in participants}
    result = _result_shell(ids)
    for public_id in ids:
        participant = by_id.get(public_id)
        if participant is None:
            result["skipped_count"] += 1
            result["failures"].append({"public_id": public_id, "message": "Participant not found"})
            continue
        result["eligible_count"] += 1
        try:
            release_participant_feedback(db, participant=participant, researcher_id=researcher.id)
            result["succeeded_count"] += 1
        except ParticipantFeedbackError as exc:
            result["failed_count"] += 1
            result["failures"].append({"public_id": public_id, "message": exc.message})
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        event_type="bulk.feedback.release",
        metadata={"requested": result["requested_count"], "succeeded": result["succeeded_count"]},
    )
    return result


def bulk_revoke_feedback(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    participants = _participants_by_public_ids(db, ids)
    by_id = {participant.public_id: participant for participant in participants}
    result = _result_shell(ids)
    for public_id in ids:
        participant = by_id.get(public_id)
        if participant is None:
            result["skipped_count"] += 1
            continue
        result["eligible_count"] += 1
        revoke_participant_feedback(db, participant=participant, researcher_id=researcher.id)
        result["succeeded_count"] += 1
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        event_type="bulk.feedback.revoke",
        metadata={"requested": result["requested_count"], "succeeded": result["succeeded_count"]},
    )
    return result


def bulk_refresh_feedback(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    participants = _participants_by_public_ids(db, ids)
    by_id = {participant.public_id: participant for participant in participants}
    result = _result_shell(ids)
    for public_id in ids:
        participant = by_id.get(public_id)
        if participant is None:
            result["skipped_count"] += 1
            continue
        result["eligible_count"] += 1
        try:
            refresh_participant_feedback(db, participant=participant, researcher_id=researcher.id)
            result["succeeded_count"] += 1
        except ParticipantFeedbackError as exc:
            result["failed_count"] += 1
            result["failures"].append({"public_id": public_id, "message": exc.message})
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        event_type="bulk.feedback.refresh",
        metadata={"requested": result["requested_count"], "succeeded": result["succeeded_count"]},
    )
    return result


def bulk_suspend(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
    duration: str,
    reason: str | None,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    result = _result_shell(ids)
    for public_id in ids:
        result["eligible_count"] += 1
        try:
            suspend_participant(db, public_id=public_id, researcher=researcher, duration=duration, reason=reason or "")
            result["succeeded_count"] += 1
        except AccountError as exc:
            result["failed_count"] += 1
            result["failures"].append({"public_id": public_id, "message": exc.message})
    record_audit_event(db, actor_type="researcher", actor_id=researcher.id, event_type="bulk.suspend", metadata=result)
    return result


def bulk_reactivate(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
    reason: str | None,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    result = _result_shell(ids)
    for public_id in ids:
        result["eligible_count"] += 1
        try:
            unsuspend_participant(db, public_id=public_id, researcher=researcher, reason=reason or "")
            result["succeeded_count"] += 1
        except AccountError as exc:
            result["failed_count"] += 1
            result["failures"].append({"public_id": public_id, "message": exc.message})
    record_audit_event(db, actor_type="researcher", actor_id=researcher.id, event_type="bulk.reactivate", metadata=result)
    return result


def bulk_remove(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
    reason: str,
) -> dict[str, Any]:
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    if len(ids) > MAX_BULK_IDS:
        raise BulkActionError(f"Maximum {MAX_BULK_IDS} participants per batch", status_code=422)
    result = _result_shell(ids)
    for public_id in ids:
        result["eligible_count"] += 1
        try:
            remove_participant_access(
                db,
                public_id=public_id,
                researcher=researcher,
                reason=reason,
                confirmation_public_id=public_id,
            )
            result["succeeded_count"] += 1
        except AccountError as exc:
            result["failed_count"] += 1
            result["failures"].append({"public_id": public_id, "message": exc.message})
    record_audit_event(db, actor_type="researcher", actor_id=researcher.id, event_type="bulk.remove", metadata=result)
    return result


def bulk_email(
    db: Session,
    *,
    researcher: Researcher,
    participant_public_ids: list[str] | None,
    selection_mode: str | None,
    filters: dict[str, Any] | None,
    excluded_public_ids: list[str] | None,
    subject: str,
    body: str,
) -> dict[str, Any]:
    if not email_is_configured():
        raise BulkActionError("Email is not configured", status_code=503)
    ids = _resolve_public_ids(
        db,
        participant_public_ids=participant_public_ids,
        selection_mode=selection_mode,
        filters=filters,
        excluded_public_ids=excluded_public_ids,
    )
    return send_bulk_email(db, public_ids=ids[:MAX_BULK_IDS], subject=subject, body=body, researcher_id=researcher.id)
