"""Auto Data date-range scheduling, preview, and batched backfill."""

from __future__ import annotations

import random
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterator
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.golden_auto_session_event import GoldenAutoSessionEvent
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.services.audit_service import record_audit_event
from app.services.golden_vault_auto_session_service import (
    AUTO_WINDOW_END_MINUTE,
    AUTO_WINDOW_START_MINUTE,
    _award_auto_session_for_date,
    _random_minute_for_date,
    _schedule_seed,
    compute_next_auto_session_at,
    is_auto_session_eligible,
)
from app.services.golden_vault_profile import apply_profile_to_override, generate_demo_profile
from app.services.study_frequency import (
    STUDY_FREQUENCY_DAILY,
    STUDY_FREQUENCY_FOUR_TIMES_WEEKLY,
    STUDY_FREQUENCY_TWICE_WEEKLY,
    STUDY_FREQUENCY_WEEKLY,
)

AUTO_DATA_FREQUENCIES = frozenset(
    {
        STUDY_FREQUENCY_DAILY,
        STUDY_FREQUENCY_WEEKLY,
        STUDY_FREQUENCY_TWICE_WEEKLY,
        STUDY_FREQUENCY_FOUR_TIMES_WEEKLY,
    }
)

FREQUENCY_WEEKDAY_COUNTS = {
    STUDY_FREQUENCY_DAILY: 7,
    STUDY_FREQUENCY_WEEKLY: 1,
    STUDY_FREQUENCY_TWICE_WEEKLY: 2,
    STUDY_FREQUENCY_FOUR_TIMES_WEEKLY: 4,
}

EXPLICIT_BACKFILL_BATCH_SIZE = 100


def _study_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().study_timezone)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _today_local() -> date:
    return _now_utc().astimezone(_study_tz()).date()


def map_participant_frequency(study_frequency: str | None) -> str:
    if study_frequency in AUTO_DATA_FREQUENCIES:
        return study_frequency
    return STUDY_FREQUENCY_DAILY


def default_weekdays_for_frequency(*, frequency: str, seed: int) -> list[int]:
    rng = random.Random(seed)
    if frequency == STUDY_FREQUENCY_DAILY:
        return list(range(7))
    count = FREQUENCY_WEEKDAY_COUNTS.get(frequency, 1)
    if count >= 7:
        return list(range(7))
    return sorted(rng.sample(range(7), count))


def normalize_weekdays(*, frequency: str, weekdays: list[int] | None, seed: int) -> list[int]:
    expected = FREQUENCY_WEEKDAY_COUNTS.get(frequency, 7)
    if frequency == STUDY_FREQUENCY_DAILY:
        return list(range(7))
    cleaned = sorted({int(d) for d in (weekdays or []) if 0 <= int(d) <= 6})
    if len(cleaned) == expected:
        return cleaned
    return default_weekdays_for_frequency(frequency=frequency, seed=seed)


def validate_auto_data_config(
    *,
    start_date: date,
    end_date: date | None,
    frequency: str,
    weekdays: list[int] | None,
    seed: int,
) -> tuple[str, list[int]]:
    if frequency not in AUTO_DATA_FREQUENCIES:
        raise ValueError("Invalid auto data frequency")
    if end_date is not None and end_date < start_date:
        raise ValueError("End date must be on or after start date")
    normalized = normalize_weekdays(frequency=frequency, weekdays=weekdays, seed=seed)
    expected = FREQUENCY_WEEKDAY_COUNTS[frequency]
    if frequency != STUDY_FREQUENCY_DAILY and len(normalized) != expected:
        raise ValueError(f"Select exactly {expected} weekday(s) for this frequency")
    return frequency, normalized


def _effective_end(end_date: date | None, *, through: date) -> date:
    if end_date is None:
        return through
    return min(end_date, through)


def _is_scheduled_weekday(local_d: date, frequency: str, weekdays: list[int]) -> bool:
    if frequency == STUDY_FREQUENCY_DAILY:
        return True
    return local_d.weekday() in weekdays


def iter_scheduled_dates(
    *,
    start_date: date,
    end_date: date | None,
    frequency: str,
    weekdays: list[int],
    through_local: date,
) -> Iterator[date]:
    end = _effective_end(end_date, through=through_local)
    if start_date > end:
        return
    current = start_date
    while current <= end:
        if _is_scheduled_weekday(current, frequency, weekdays):
            yield current
        current += timedelta(days=1)


def scheduled_datetime_for_date(row: GoldenDemoOverride, local_d: date) -> datetime:
    seed = _schedule_seed(row)
    minute = _random_minute_for_date(seed=seed, local_date=local_d)
    tz = _study_tz()
    hour, minu = divmod(minute, 60)
    local = datetime(local_d.year, local_d.month, local_d.day, hour, minu, tzinfo=tz)
    return local.astimezone(UTC)


def is_date_due_for_backfill(*, local_d: date, scheduled_utc: datetime, now: datetime) -> bool:
    if local_d < _today_local():
        return True
    if local_d > _today_local():
        return False
    if scheduled_utc.tzinfo is None:
        scheduled_utc = scheduled_utc.replace(tzinfo=UTC)
    return scheduled_utc <= now


def count_existing_events(db: Session, participant_id: UUID, dates: list[date]) -> int:
    if not dates:
        return 0
    return db.execute(
        select(func.count())
        .select_from(GoldenAutoSessionEvent)
        .where(
            GoldenAutoSessionEvent.participant_id == participant_id,
            GoldenAutoSessionEvent.local_session_date.in_(dates),
        )
    ).scalar_one()


def list_due_backfill_dates(
    row: GoldenDemoOverride,
    *,
    now: datetime | None = None,
    through_local: date | None = None,
) -> list[date]:
    if row.auto_data_start_date is None or not row.auto_data_frequency:
        return []
    ref = now or _now_utc()
    through = through_local or _today_local()
    weekdays = normalize_weekdays(
        frequency=row.auto_data_frequency,
        weekdays=row.auto_data_weekdays_json,
        seed=_schedule_seed(row),
    )
    due: list[date] = []
    for local_d in iter_scheduled_dates(
        start_date=row.auto_data_start_date,
        end_date=row.auto_data_end_date,
        frequency=row.auto_data_frequency,
        weekdays=weekdays,
        through_local=through,
    ):
        scheduled = scheduled_datetime_for_date(row, local_d)
        if is_date_due_for_backfill(local_d=local_d, scheduled_utc=scheduled, now=ref):
            due.append(local_d)
    return due


def compute_auto_data_preview(
    db: Session,
    *,
    participant: Participant,
    row: GoldenDemoOverride,
    start_date: date,
    end_date: date | None,
    frequency: str,
    weekdays: list[int] | None,
    real_completed_sessions: int,
) -> dict[str, Any]:
    seed = _schedule_seed(row)
    frequency, normalized_weekdays = validate_auto_data_config(
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        weekdays=weekdays,
        seed=seed,
    )
    now = _now_utc()
    through = _today_local()
    scheduled_all: list[date] = []
    for local_d in iter_scheduled_dates(
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        weekdays=normalized_weekdays,
        through_local=through,
    ):
        scheduled = scheduled_datetime_for_date(row, local_d)
        if is_date_due_for_backfill(local_d=local_d, scheduled_utc=scheduled, now=now):
            scheduled_all.append(local_d)

    existing = 0
    if scheduled_all:
        existing = count_existing_events(db, participant.id, scheduled_all)
    new_count = max(0, len(scheduled_all) - existing)

    bonus = max(0, int(row.bonus_sessions or 0))
    if row.is_auto_data_user:
        displayed = bonus
    else:
        displayed = real_completed_sessions + bonus

    next_future = next_future_session(row, start_date=start_date, end_date=end_date, frequency=frequency, weekdays=normalized_weekdays)

    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat() if end_date else None,
        "endLabel": "Never" if end_date is None else end_date.isoformat(),
        "frequency": frequency,
        "weekdays": normalized_weekdays,
        "scheduledThroughToday": len(scheduled_all),
        "alreadyGenerated": existing,
        "newSessionsToAdd": new_count,
        "resultingDisplayedSessions": displayed + new_count,
        "nextAutoSessionAt": next_future.isoformat() if next_future else None,
    }


def next_future_session(
    row: GoldenDemoOverride,
    *,
    start_date: date,
    end_date: date | None,
    frequency: str,
    weekdays: list[int],
    after_local: date | None = None,
) -> datetime | None:
    tz = _study_tz()
    ref_local = after_local or _today_local()
    if end_date is not None and ref_local > end_date:
        return None
    search_start = max(start_date, ref_local)
    horizon = search_start + timedelta(days=366 * 6)
    end_bound = end_date or horizon
    current = search_start
    while current <= end_bound:
        if _is_scheduled_weekday(current, frequency, weekdays):
            scheduled = scheduled_datetime_for_date(row, current)
            if current > ref_local or scheduled > _now_utc():
                return scheduled
        current += timedelta(days=1)
    return None


def refresh_next_auto_session_from_config(db: Session, row: GoldenDemoOverride, participant: Participant) -> None:
    if not row.auto_session_enabled or row.auto_data_start_date is None or not row.auto_data_frequency:
        return
    weekdays = normalize_weekdays(
        frequency=row.auto_data_frequency,
        weekdays=row.auto_data_weekdays_json,
        seed=_schedule_seed(row),
    )
    nxt = next_future_session(
        row,
        start_date=row.auto_data_start_date,
        end_date=row.auto_data_end_date,
        frequency=row.auto_data_frequency,
        weekdays=weekdays,
    )
    row.next_auto_session_at = nxt


def apply_auto_data_config(
    db: Session,
    *,
    participant: Participant,
    row: GoldenDemoOverride,
    start_date: date,
    end_date: date | None,
    frequency: str,
    weekdays: list[int] | None,
    enable_future: bool = True,
) -> None:
    if not row.random_seed:
        apply_profile_to_override(row, generate_demo_profile())
    seed = _schedule_seed(row)
    frequency, normalized = validate_auto_data_config(
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        weekdays=weekdays,
        seed=seed,
    )
    row.auto_data_start_date = start_date
    row.auto_data_end_date = end_date
    row.auto_data_frequency = frequency
    row.auto_data_weekdays_json = normalized
    row.auto_data_configured_at = _now_utc()
    row.is_auto_data_user = True
    row.enabled = True
    if enable_future:
        row.auto_session_enabled = True
    refresh_next_auto_session_from_config(db, row, participant)
    row.auto_session_updated_at = _now_utc()
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_data_configured",
        participant_id=participant.id,
        metadata={
            "participant_public_id": participant.public_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "frequency": frequency,
        },
    )


def apply_backfill_batch(
    db: Session,
    *,
    participant: Participant,
    row: GoldenDemoOverride,
    limit: int = EXPLICIT_BACKFILL_BATCH_SIZE,
) -> dict[str, int]:
    if not is_auto_session_eligible(participant):
        return {"requested": 0, "created": 0, "skipped": 0}

    due_dates = list_due_backfill_dates(row)
    if not due_dates:
        return {"requested": 0, "created": 0, "skipped": 0}

    existing_dates = set(
        db.execute(
            select(GoldenAutoSessionEvent.local_session_date).where(
                GoldenAutoSessionEvent.participant_id == participant.id,
                GoldenAutoSessionEvent.local_session_date.in_(due_dates),
            )
        ).scalars().all()
    )
    to_create = [d for d in due_dates if d not in existing_dates][:limit]
    created = 0
    skipped = len(due_dates) - len(to_create) - len(existing_dates.intersection(due_dates))

    for local_d in to_create:
        scheduled = scheduled_datetime_for_date(row, local_d)
        if _award_auto_session_for_date(
            db,
            participant=participant,
            row=row,
            local_session_date=local_d,
            scheduled_for=scheduled,
            manual=False,
        ):
            created += 1
            row.is_auto_data_user = True

    if created:
        row.auto_data_last_reconciled_at = _now_utc()
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.auto_data_backfill_batch",
            participant_id=participant.id,
            metadata={
                "participant_public_id": participant.public_id,
                "created": created,
                "batch_limit": limit,
            },
        )
    refresh_next_auto_session_from_config(db, row, participant)
    remaining = max(0, len([d for d in due_dates if d not in existing_dates]) - created)
    return {"requested": len(to_create), "created": created, "skipped": skipped, "remaining": remaining}


def pause_auto_data(db: Session, row: GoldenDemoOverride, participant: Participant) -> None:
    row.auto_session_enabled = False
    row.auto_session_updated_at = _now_utc()
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_data_paused",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )


def resume_auto_data(db: Session, row: GoldenDemoOverride, participant: Participant) -> None:
    row.auto_session_enabled = True
    refresh_next_auto_session_from_config(db, row, participant)
    row.auto_session_updated_at = _now_utc()
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_data_resumed",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )


def auto_data_fields_for_row(row: GoldenDemoOverride | None) -> dict[str, Any]:
    if row is None:
        return {
            "autoDataConfigured": False,
            "autoDataStartDate": None,
            "autoDataEndDate": None,
            "autoDataFrequency": None,
            "autoDataWeekdays": None,
            "autoDataPaused": False,
        }
    return {
        "autoDataConfigured": row.auto_data_start_date is not None,
        "autoDataStartDate": row.auto_data_start_date.isoformat() if row.auto_data_start_date else None,
        "autoDataEndDate": row.auto_data_end_date.isoformat() if row.auto_data_end_date else None,
        "autoDataFrequency": row.auto_data_frequency,
        "autoDataWeekdays": row.auto_data_weekdays_json,
        "autoDataPaused": bool(row.auto_data_start_date and not row.auto_session_enabled),
    }
