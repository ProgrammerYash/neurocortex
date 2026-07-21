"""Researcher-to-participant inbox messaging."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.participant import Participant
from app.models.participant_message import ParticipantMessage
from app.models.researcher import Researcher

STUDY_TIMEZONE = ZoneInfo("America/New_York")
MAX_SUBJECT_LENGTH = 150
MAX_BODY_LENGTH = 5000


class MessageError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        error_code: str | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def format_study_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    local = value.astimezone(STUDY_TIMEZONE)
    return local.strftime("%b %d, %Y %I:%M %p").lstrip("0").replace(" 0", " ")


def _validate_subject(subject: str) -> str:
    cleaned = subject.strip()
    if not cleaned:
        raise MessageError("Subject is required.")
    if len(cleaned) > MAX_SUBJECT_LENGTH:
        raise MessageError(f"Subject must be at most {MAX_SUBJECT_LENGTH} characters.")
    return cleaned


def _validate_body(body: str) -> str:
    cleaned = body.strip()
    if not cleaned:
        raise MessageError("Message body is required.")
    if len(cleaned) > MAX_BODY_LENGTH:
        raise MessageError(f"Message body must be at most {MAX_BODY_LENGTH} characters.")
    return cleaned


def _get_participant_by_public_id(db: Session, public_id: str) -> Participant:
    participant = db.execute(
        select(Participant).where(Participant.public_id == public_id)
    ).scalar_one_or_none()
    if participant is None:
        raise MessageError("Participant not found", status_code=404, error_code="PARTICIPANT_NOT_FOUND")
    return participant


def _serialize_message(message: ParticipantMessage) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "participantId": message.participant.public_id if message.participant else None,
        "subject": message.subject,
        "body": message.body,
        "createdAt": message.created_at,
        "createdAtDisplay": format_study_datetime(message.created_at),
        "readAt": message.read_at,
        "readAtDisplay": format_study_datetime(message.read_at),
        "isRead": message.read_at is not None,
        "researcherDisplayName": message.researcher.display_name if message.researcher else "NeuroCortex Research Team",
    }


def _recent_duplicate(
    db: Session,
    *,
    participant_id: UUID,
    researcher_id: UUID,
    subject: str,
    body: str,
    window_seconds: int = 3,
) -> ParticipantMessage | None:
    cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)
    return db.execute(
        select(ParticipantMessage)
        .where(
            ParticipantMessage.participant_id == participant_id,
            ParticipantMessage.researcher_id == researcher_id,
            ParticipantMessage.subject == subject,
            ParticipantMessage.body == body,
            ParticipantMessage.created_at >= cutoff,
        )
        .order_by(ParticipantMessage.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def send_participant_message(
    db: Session,
    *,
    public_id: str,
    researcher: Researcher,
    subject: str,
    body: str,
) -> dict[str, Any]:
    participant = _get_participant_by_public_id(db, public_id)
    if participant.removed_at is not None:
        raise MessageError(
            "Removed participants cannot receive new messages.",
            status_code=409,
            error_code="PARTICIPANT_REMOVED",
        )
    cleaned_subject = _validate_subject(subject)
    cleaned_body = _validate_body(body)
    duplicate = _recent_duplicate(
        db,
        participant_id=participant.id,
        researcher_id=researcher.id,
        subject=cleaned_subject,
        body=cleaned_body,
    )
    if duplicate is not None:
        db.refresh(duplicate, attribute_names=["participant", "researcher"])
        return _serialize_message(duplicate)

    message = ParticipantMessage(
        participant_id=participant.id,
        researcher_id=researcher.id,
        subject=cleaned_subject,
        body=cleaned_body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    message.participant = participant
    message.researcher = researcher
    return _serialize_message(message)


def list_researcher_participant_messages(
    db: Session,
    *,
    public_id: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    participant = _get_participant_by_public_id(db, public_id)
    total = db.execute(
        select(func.count())
        .select_from(ParticipantMessage)
        .where(ParticipantMessage.participant_id == participant.id)
    ).scalar_one()
    messages = db.execute(
        select(ParticipantMessage)
        .options(selectinload(ParticipantMessage.participant), selectinload(ParticipantMessage.researcher))
        .where(ParticipantMessage.participant_id == participant.id)
        .order_by(ParticipantMessage.created_at.desc(), ParticipantMessage.id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return [_serialize_message(message) for message in messages], int(total)


def list_participant_messages(
    db: Session,
    *,
    participant_id: UUID,
    limit: int,
    offset: int,
    unread_only: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    filters = [ParticipantMessage.participant_id == participant_id]
    if unread_only:
        filters.append(ParticipantMessage.read_at.is_(None))
    total = db.execute(
        select(func.count()).select_from(ParticipantMessage).where(*filters)
    ).scalar_one()
    messages = db.execute(
        select(ParticipantMessage)
        .options(selectinload(ParticipantMessage.researcher))
        .where(*filters)
        .order_by(ParticipantMessage.created_at.desc(), ParticipantMessage.id.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return [_serialize_message(message) for message in messages], int(total)


def unread_message_count(db: Session, *, participant_id: UUID) -> int:
    return db.execute(
        select(func.count())
        .select_from(ParticipantMessage)
        .where(
            ParticipantMessage.participant_id == participant_id,
            ParticipantMessage.read_at.is_(None),
        )
    ).scalar_one()


def mark_message_read(
    db: Session,
    *,
    participant_id: UUID,
    message_id: UUID,
) -> dict[str, Any]:
    message = db.execute(
        select(ParticipantMessage)
        .options(selectinload(ParticipantMessage.researcher), selectinload(ParticipantMessage.participant))
        .where(
            ParticipantMessage.id == message_id,
            ParticipantMessage.participant_id == participant_id,
        )
    ).scalar_one_or_none()
    if message is None:
        raise MessageError("Message not found", status_code=404, error_code="MESSAGE_NOT_FOUND")
    if message.read_at is None:
        message.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(message)
    return _serialize_message(message)
