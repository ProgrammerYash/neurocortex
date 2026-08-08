"""Effective enrollment dates for real and synthetic participants."""

from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.daily_session import DailySession
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.services.consent_content import CONSENT_VERSION

STUDY_TIMEZONE = ZoneInfo("America/New_York")


def enrollment_datetime_from_study_date(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    return datetime.combine(value, time(12, 0), tzinfo=STUDY_TIMEZONE).astimezone(UTC)


def resolve_synthetic_enrollment_at(
    db: Session,
    *,
    participant: Participant,
    override: GoldenDemoOverride | None,
) -> datetime | None:
    if override is None or not override.is_synthetic_generated:
        return None
    if override.synthetic_enrollment_at is not None:
        return override.synthetic_enrollment_at
    if override.auto_data_start_date is not None:
        return enrollment_datetime_from_study_date(override.auto_data_start_date)
    earliest_session = db.execute(
        select(DailySession.session_date)
        .where(DailySession.participant_id == participant.id)
        .order_by(DailySession.session_date.asc())
        .limit(1)
    ).scalar_one_or_none()
    if earliest_session is not None:
        return enrollment_datetime_from_study_date(earliest_session)
    record = db.execute(
        select(ConsentRecord.participant_signed_at)
        .where(
            ConsentRecord.participant_id == participant.id,
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
        .order_by(ConsentRecord.created_at.asc())
        .limit(1)
    ).scalar_one_or_none()
    if record is not None:
        return record
    return participant.created_at


def effective_participant_enrollment_at(
    db: Session,
    *,
    participant: Participant,
    override: GoldenDemoOverride | None = None,
) -> datetime:
    synthetic = resolve_synthetic_enrollment_at(db, participant=participant, override=override)
    if synthetic is not None:
        return synthetic
    return participant.created_at


def backfill_synthetic_enrollment(db: Session, *, participant_id, enrollment_at: datetime) -> None:
    override = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant_id)
    ).scalar_one_or_none()
    if override is None or not override.is_synthetic_generated:
        return
    if override.synthetic_enrollment_at is None:
        override.synthetic_enrollment_at = enrollment_at
    participant = db.get(Participant, participant_id)
    if participant is not None and participant.created_at > enrollment_at:
        participant.created_at = enrollment_at
