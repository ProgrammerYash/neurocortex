"""Golden Vault automatic bonus session scheduling and processing."""

from __future__ import annotations

import random
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.golden_auto_session_event import GoldenAutoSessionEvent
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.services.audit_service import record_audit_event
from app.services.golden_vault_profile import apply_profile_to_override, generate_demo_profile
from app.services.participant_account_service import is_effectively_suspended

AUTO_WINDOW_START_MINUTE = 14 * 60
AUTO_WINDOW_END_MINUTE = 20 * 60
MIN_REMAINING_BEFORE_TOMORROW = timedelta(minutes=5)

METRIC_CLAMP = {
    "simulated_reaction_ms": (230.0, 650.0),
    "simulated_stress": (1.5, 8.8),
    "simulated_fatigue": (1.5, 8.8),
    "simulated_sleep_hours": (4.5, 9.5),
    "simulated_memory_percent": (55.0, 98.0),
    "simulated_session_completion_percent": (75.0, 100.0),
}

METRIC_DELTAS = {
    "simulated_reaction_ms": (-15.0, 15.0),
    "simulated_stress": (-0.3, 0.3),
    "simulated_fatigue": (-0.3, 0.3),
    "simulated_sleep_hours": (-0.2, 0.2),
    "simulated_memory_percent": (-2.0, 2.0),
    "simulated_session_completion_percent": (-1.0, 1.0),
}


def _study_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().study_timezone)


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _minute_of_day_to_local_datetime(local_date: date, minute_of_day: int, tz: ZoneInfo) -> datetime:
    hour, minute = divmod(int(minute_of_day), 60)
    local = datetime(local_date.year, local_date.month, local_date.day, hour, minute, tzinfo=tz)
    return local.astimezone(UTC)


def _random_minute_for_date(*, seed: int, local_date: date) -> int:
    rng = random.Random(seed ^ hash(local_date.isoformat()))
    return rng.randint(AUTO_WINDOW_START_MINUTE, AUTO_WINDOW_END_MINUTE)


def _schedule_seed(row: GoldenDemoOverride) -> int:
    return int(row.random_seed or int.from_bytes(row.participant_id.bytes[:4], "big"))


def compute_next_auto_session_at(
    row: GoldenDemoOverride,
    *,
    reference: datetime | None = None,
    local_date: date | None = None,
) -> datetime:
    """Pick persisted random time for first schedule or a specific local calendar day."""
    tz = _study_tz()
    ref = reference or _now_utc()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    local_now = ref.astimezone(tz)
    target_date = local_date or local_now.date()
    seed = _schedule_seed(row)
    minute = _random_minute_for_date(seed=seed, local_date=target_date)
    scheduled_local = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        minute // 60,
        minute % 60,
        tzinfo=tz,
    )
    return scheduled_local.astimezone(UTC)


def compute_initial_next_auto_session_at(row: GoldenDemoOverride, *, now: datetime | None = None) -> datetime:
    tz = _study_tz()
    ref = now or _now_utc()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    local_now = ref.astimezone(tz)
    window_start = local_now.replace(hour=14, minute=0, second=0, microsecond=0)
    window_end = local_now.replace(hour=20, minute=0, second=0, microsecond=0)

    if local_now < window_start:
        return compute_next_auto_session_at(row, reference=ref, local_date=local_now.date())
    if local_now <= window_end:
        remaining = window_end - local_now
        if remaining >= MIN_REMAINING_BEFORE_TOMORROW:
            return compute_next_auto_session_at(row, reference=ref, local_date=local_now.date())
        tomorrow = local_now.date() + timedelta(days=1)
        return compute_next_auto_session_at(row, reference=ref, local_date=tomorrow)
    tomorrow = local_now.date() + timedelta(days=1)
    return compute_next_auto_session_at(row, reference=ref, local_date=tomorrow)


def is_auto_session_eligible(participant: Participant) -> bool:
    if participant.removed_at is not None:
        return False
    if is_effectively_suspended(participant):
        return False
    return True


def _snapshot_metrics(row: GoldenDemoOverride) -> dict[str, Any]:
    return {
        "simulated_reaction_ms": row.simulated_reaction_ms,
        "simulated_stress": row.simulated_stress,
        "simulated_fatigue": row.simulated_fatigue,
        "simulated_sleep_hours": row.simulated_sleep_hours,
        "simulated_memory_percent": row.simulated_memory_percent,
        "simulated_session_completion_percent": row.simulated_session_completion_percent,
        "bonus_sessions": row.bonus_sessions,
    }


def _apply_metric_deltas(row: GoldenDemoOverride, local_session_date: date) -> None:
    if row.simulated_reaction_ms is None:
        apply_profile_to_override(row, generate_demo_profile(seed=row.random_seed))
    seed = _schedule_seed(row) ^ hash(local_session_date.isoformat())
    rng = random.Random(seed)
    for field, (low_d, high_d) in METRIC_DELTAS.items():
        current = getattr(row, field)
        if current is None:
            continue
        delta = rng.uniform(low_d, high_d)
        clamp_low, clamp_high = METRIC_CLAMP[field]
        if field == "simulated_reaction_ms":
            value = round(max(clamp_low, min(clamp_high, float(current) + delta)))
        elif field == "simulated_memory_percent" or field == "simulated_session_completion_percent":
            value = round(max(clamp_low, min(clamp_high, float(current) + delta)), 1)
        else:
            value = round(max(clamp_low, min(clamp_high, float(current) + delta)), 1)
        setattr(row, field, value)
    if row.simulated_feedback_status != "Released":
        row.simulated_feedback_status = "Released"


def _set_last_active_from_scheduled(row: GoldenDemoOverride, scheduled_for: datetime) -> None:
    tz = _study_tz()
    if scheduled_for.tzinfo is None:
        scheduled_for = scheduled_for.replace(tzinfo=UTC)
    local = scheduled_for.astimezone(tz)
    row.last_active_minute_of_day = local.hour * 60 + local.minute


def _award_auto_session_for_date(
    db: Session,
    *,
    participant: Participant,
    row: GoldenDemoOverride,
    local_session_date: date,
    scheduled_for: datetime,
    manual: bool = False,
) -> bool:
    """Returns True if a new session was awarded."""
    if not is_auto_session_eligible(participant):
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.auto_session_skipped_ineligible",
            participant_id=participant.id,
            metadata={"participant_public_id": participant.public_id, "reason": "suspended_or_removed"},
        )
        return False

    existing = db.execute(
        select(GoldenAutoSessionEvent.id).where(
            GoldenAutoSessionEvent.participant_id == participant.id,
            GoldenAutoSessionEvent.local_session_date == local_session_date,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False

    before = _snapshot_metrics(row)
    event = GoldenAutoSessionEvent(
        participant_id=participant.id,
        scheduled_for=scheduled_for,
        local_session_date=local_session_date,
        processed_at=_now_utc(),
        bonus_session_delta=1,
        metrics_before_json=before,
    )
    db.add(event)
    db.flush()

    row.bonus_sessions = max(0, int(row.bonus_sessions or 0)) + 1
    _apply_metric_deltas(row, local_session_date)
    after = _snapshot_metrics(row)
    event.metrics_after_json = after
    row.last_auto_session_at = scheduled_for
    row.last_auto_session_local_date = local_session_date
    _set_last_active_from_scheduled(row, scheduled_for)
    row.auto_session_updated_at = _now_utc()
    row.updated_at = _now_utc()

    next_day = local_session_date + timedelta(days=1)
    row.next_auto_session_at = compute_next_auto_session_at(row, local_date=next_day)

    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_session_run_manual" if manual else "golden_vault.auto_session_run_auto",
        participant_id=participant.id,
        metadata={
            "participant_public_id": participant.public_id,
            "local_session_date": local_session_date.isoformat(),
        },
    )
    db.flush()
    return True


def enable_auto_session(db: Session, row: GoldenDemoOverride, participant: Participant) -> None:
    if not row.random_seed:
        apply_profile_to_override(row, generate_demo_profile())
    row.auto_session_enabled = True
    row.next_auto_session_at = compute_initial_next_auto_session_at(row)
    row.auto_session_updated_at = _now_utc()
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_session_enabled",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )


def disable_auto_session(db: Session, row: GoldenDemoOverride, participant: Participant) -> None:
    row.auto_session_enabled = False
    row.auto_session_updated_at = _now_utc()
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_session_disabled",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )


def reschedule_auto_session(db: Session, row: GoldenDemoOverride, participant: Participant) -> None:
    if not row.auto_session_enabled:
        raise ValueError("Auto session is not enabled")
    row.next_auto_session_at = compute_initial_next_auto_session_at(row)
    row.auto_session_updated_at = _now_utc()
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_session_rescheduled",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )


def run_auto_session_now(db: Session, row: GoldenDemoOverride, participant: Participant) -> bool:
    tz = _study_tz()
    local_today = _now_utc().astimezone(tz).date()
    scheduled = row.next_auto_session_at or compute_next_auto_session_at(row, local_date=local_today)
    if scheduled.astimezone(tz).date() != local_today:
        scheduled = compute_next_auto_session_at(row, local_date=local_today)
    return _award_auto_session_for_date(
        db,
        participant=participant,
        row=row,
        local_session_date=local_today,
        scheduled_for=scheduled,
        manual=True,
    )


def process_due_golden_auto_sessions(
    db: Session,
    *,
    batch_size: int | None = None,
    max_catchup_days: int | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    settings = get_settings()
    if not settings.golden_auto_sessions_enabled:
        return {"processed": 0, "awarded": 0, "skipped": 0, "errors": 0}

    batch_size = batch_size or settings.golden_auto_session_batch_size
    max_catchup_days = max_catchup_days or settings.golden_auto_session_max_catchup_days
    ref = now or _now_utc()
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)

    summary = {"processed": 0, "awarded": 0, "skipped": 0, "errors": 0}
    tz = _study_tz()

    due_ids = db.execute(
        select(GoldenDemoOverride.id)
        .where(
            GoldenDemoOverride.auto_session_enabled.is_(True),
            GoldenDemoOverride.next_auto_session_at.isnot(None),
            GoldenDemoOverride.next_auto_session_at <= ref,
        )
        .order_by(GoldenDemoOverride.next_auto_session_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    ).scalars().all()

    for override_id in due_ids:
        summary["processed"] += 1
        try:
            row = db.get(GoldenDemoOverride, override_id)
            if row is None or not row.auto_session_enabled or row.next_auto_session_at is None:
                summary["skipped"] += 1
                continue
            participant = db.get(Participant, row.participant_id)
            if participant is None:
                summary["skipped"] += 1
                continue
            if not is_auto_session_eligible(participant):
                summary["skipped"] += 1
                continue

            catchup = 0
            while (
                row.next_auto_session_at is not None
                and row.next_auto_session_at <= ref
                and catchup < max_catchup_days
            ):
                local_date = row.next_auto_session_at.astimezone(tz).date()
                scheduled = row.next_auto_session_at
                awarded = _award_auto_session_for_date(
                    db,
                    participant=participant,
                    row=row,
                    local_session_date=local_date,
                    scheduled_for=scheduled,
                    manual=False,
                )
                if awarded:
                    summary["awarded"] += 1
                    catchup += 1
                else:
                    row.next_auto_session_at = compute_next_auto_session_at(
                        row,
                        local_date=local_date + timedelta(days=1),
                    )
                    db.flush()
                    catchup += 1
        except Exception:
            summary["errors"] += 1

    if summary["awarded"] > 0:
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.auto_session_processor_run",
            metadata={"awarded": summary["awarded"], "processed": summary["processed"]},
        )
    return summary


def maybe_process_due_auto_sessions(db: Session, *, batch_size: int = 25) -> dict[str, int]:
    """Bounded catch-up for request paths (list load, startup, dashboard)."""
    started = time.perf_counter()
    result = process_due_golden_auto_sessions(db, batch_size=batch_size)
    result["elapsed_ms"] = int((time.perf_counter() - started) * 1000)
    return result


def auto_session_fields_for_row(row: GoldenDemoOverride | None) -> dict[str, Any]:
    if row is None:
        return {
            "autoSessionEnabled": False,
            "nextAutoSessionAt": None,
            "nextAutoSessionDisplay": None,
            "lastAutoSessionAt": None,
            "lastAutoSessionDisplay": None,
        }
    from app.services.researcher_dashboard_service import format_study_datetime

    next_at = row.next_auto_session_at.isoformat() if row.next_auto_session_at else None
    last_at = row.last_auto_session_at.isoformat() if row.last_auto_session_at else None
    return {
        "autoSessionEnabled": bool(row.auto_session_enabled),
        "nextAutoSessionAt": next_at,
        "nextAutoSessionDisplay": format_study_datetime(row.next_auto_session_at) if row.next_auto_session_at else None,
        "lastAutoSessionAt": last_at,
        "lastAutoSessionDisplay": format_study_datetime(row.last_auto_session_at) if row.last_auto_session_at else None,
    }
