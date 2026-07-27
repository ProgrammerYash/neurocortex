"""Golden Vault demo override persistence and admin operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.models.participant_game_data import ParticipantGameData
from app.services.audit_service import record_audit_event
from app.services.consent_content import CONSENT_VERSION
from app.services.golden_vault_auto_session_service import (
    auto_session_fields_for_row,
    disable_auto_session,
    enable_auto_session,
    is_auto_session_eligible,
    maybe_process_due_auto_sessions,
    reschedule_auto_session,
    run_auto_session_now,
)
from app.services.golden_vault_auto_data_service import (
    apply_auto_data_config,
    apply_backfill_batch,
    auto_data_fields_for_row,
    compute_auto_data_preview,
    map_participant_frequency,
    pause_auto_data,
    resume_auto_data,
)
from app.services.golden_vault_display_service import resolve_participant_display_metrics
from app.services.golden_vault_profile import apply_profile_to_override, generate_demo_profile
from app.services.researcher_dashboard_service import _aggregate_sessions, _load_sessions_by_participant
from app.services.study_guard import apply_participant_filter, is_synthetic_public_id


class GoldenVaultError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def load_overrides_map(db: Session, participant_ids: list[UUID]) -> dict[UUID, GoldenDemoOverride]:
    if not participant_ids:
        return {}
    rows = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id.in_(participant_ids))
    ).scalars().all()
    return {row.participant_id: row for row in rows}


def get_override_for_participant(db: Session, participant_id: UUID) -> GoldenDemoOverride | None:
    return db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant_id)
    ).scalar_one_or_none()


def get_enabled_override(db: Session, participant_id: UUID) -> GoldenDemoOverride | None:
    row = get_override_for_participant(db, participant_id)
    if row is None or not row.enabled:
        return None
    return row


def _get_or_create_override(db: Session, participant: Participant) -> GoldenDemoOverride:
    row = get_override_for_participant(db, participant.id)
    if row is None:
        row = GoldenDemoOverride(participant_id=participant.id, enabled=False)
        db.add(row)
        db.flush()
    return row


def _touch(row: GoldenDemoOverride, *, updated_by: str = "golden_vault") -> None:
    row.updated_at = datetime.now(UTC)
    row.updated_by = updated_by


def _earned_coins_map(db: Session, participant_ids: list[UUID]) -> dict[UUID, int]:
    if not participant_ids:
        return {}
    rows = db.execute(
        select(ParticipantGameData).where(ParticipantGameData.participant_id.in_(participant_ids))
    ).scalars().all()
    result = {pid: 0 for pid in participant_ids}
    for row in rows:
        result[row.participant_id] = int((row.game_data or {}).get("coins") or 0)
    return result


def _real_completed_sessions_map(db: Session, participant_ids: list[UUID]) -> dict[UUID, int]:
    if not participant_ids:
        return {}
    sessions_map = _load_sessions_by_participant(db, participant_ids)
    return {
        pid: int(_aggregate_sessions(sessions_map.get(pid, []))["sessions_completed"])
        for pid in participant_ids
    }


def _consent_display_names(db: Session, participant_ids: list[UUID]) -> dict[UUID, str | None]:
    if not participant_ids:
        return {}
    rows = db.execute(
        select(ConsentRecord).where(
            ConsentRecord.participant_id.in_(participant_ids),
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
    ).scalars().all()
    by_participant: dict[UUID, ConsentRecord] = {}
    for row in rows:
        existing = by_participant.get(row.participant_id)
        if existing is None or row.created_at > existing.created_at:
            by_participant[row.participant_id] = row
    return {
        pid: (
            (rec.participant_printed_name or rec.guardian_printed_name)
            if (rec := by_participant.get(pid))
            else None
        )
        for pid in participant_ids
    }


def _vault_visibility_clause(now: datetime | None = None):
    ref = now or datetime.now(UTC)
    suspended_active = and_(
        Participant.is_suspended.is_(True),
        or_(Participant.suspended_until.is_(None), Participant.suspended_until > ref),
    )
    return and_(Participant.removed_at.is_(None), ~suspended_active)


def _vault_participant_query(db: Session, *, search: str | None):
    query = apply_participant_filter(select(Participant)).where(_vault_visibility_clause())
    if search and search.strip():
        query = query.where(Participant.public_id.ilike(f"%{search.strip()}%"))
    return query


def _earned_coins(db: Session, participant_id: UUID) -> int:
    return _earned_coins_map(db, [participant_id]).get(participant_id, 0)


def _real_completed_sessions(db: Session, participant_id: UUID) -> int:
    return _real_completed_sessions_map(db, [participant_id]).get(participant_id, 0)


def _consent_display_name(db: Session, participant_id: UUID) -> str | None:
    record = db.execute(
        select(ConsentRecord).where(
            ConsentRecord.participant_id == participant_id,
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if record is None:
        return None
    return record.participant_printed_name or record.guardian_printed_name


def _participant_row_payload(
    *,
    participant: Participant,
    override: GoldenDemoOverride | None,
    real_sessions: int,
    earned: int,
    display_name: str | None,
) -> dict[str, Any]:
    enabled = bool(override and override.enabled)
    bonus_sessions = max(0, int(override.bonus_sessions or 0)) if override else 0
    bonus_coins = max(0, int(override.bonus_coins or 0)) if override else 0
    display = resolve_participant_display_metrics(
        participant=participant,
        real_metrics={"sessions_completed": real_sessions, "sessions_started": real_sessions},
        golden_override=override if enabled else None,
    )
    displayed_sessions = int(display.get("displayedCompletedSessions") or real_sessions)
    payload = {
        "participantId": participant.public_id,
        "displayName": display_name,
        "enabled": enabled,
        "realCompletedSessions": real_sessions,
        "bonusSessions": bonus_sessions if enabled else 0,
        "displayedCompletedSessions": displayed_sessions,
        "earnedCoins": earned,
        "bonusCoins": bonus_coins if enabled else 0,
        "displayedCoins": earned + (bonus_coins if enabled else 0),
        "feedbackLevel": override.simulated_feedback_level if override else None,
        "feedbackStatus": override.simulated_feedback_status if override else None,
        "updatedAt": override.updated_at.isoformat() if override and override.updated_at else None,
    }
    payload.update(auto_session_fields_for_row(override))
    payload.update(auto_data_fields_for_row(override))
    return payload


def _build_vault_filtered_query(
    db: Session,
    *,
    search: str | None,
    golden_enabled: str | None,
    feedback_filter: str | None,
):
    query = _vault_participant_query(db, search=search).outerjoin(
        GoldenDemoOverride,
        GoldenDemoOverride.participant_id == Participant.id,
    )
    if golden_enabled == "enabled":
        query = query.where(GoldenDemoOverride.enabled.is_(True))
    elif golden_enabled == "disabled":
        query = query.where(or_(GoldenDemoOverride.enabled.is_(False), GoldenDemoOverride.id.is_(None)))
    if feedback_filter == "released":
        query = query.where(GoldenDemoOverride.simulated_feedback_status == "Released")
    elif feedback_filter == "revoked":
        query = query.where(GoldenDemoOverride.simulated_feedback_status == "Revoked")
    return query


def list_vault_participants(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None,
    golden_enabled: str | None,
    feedback_filter: str | None,
) -> tuple[list[dict[str, Any]], int]:
    maybe_process_due_auto_sessions(db, batch_size=25)
    filtered = _build_vault_filtered_query(
        db,
        search=search,
        golden_enabled=golden_enabled,
        feedback_filter=feedback_filter,
    )
    total = db.execute(select(func.count()).select_from(filtered.subquery())).scalar_one()
    participants = db.execute(
        filtered.order_by(Participant.created_at.asc()).offset(offset).limit(limit)
    ).scalars().all()
    participants = [p for p in participants if not is_synthetic_public_id(p.public_id)]
    if not participants:
        return [], int(total)
    ids = [p.id for p in participants]
    override_map = load_overrides_map(db, ids)
    sessions_map = _real_completed_sessions_map(db, ids)
    coins_map = _earned_coins_map(db, ids)
    names_map = _consent_display_names(db, ids)
    rows = [
        _participant_row_payload(
            participant=participant,
            override=override_map.get(participant.id),
            real_sessions=sessions_map.get(participant.id, 0),
            earned=coins_map.get(participant.id, 0),
            display_name=names_map.get(participant.id),
        )
        for participant in participants
    ]
    return rows, int(total)


def get_vault_participant(db: Session, public_id: str) -> dict[str, Any] | None:
    participant = db.execute(
        apply_participant_filter(select(Participant).where(Participant.public_id == public_id.upper()))
    ).scalar_one_or_none()
    if participant is None or is_synthetic_public_id(participant.public_id):
        return None
    if not is_auto_session_eligible(participant):
        return None
    override = get_override_for_participant(db, participant.id)
    return _participant_row_payload(
        participant=participant,
        override=override,
        real_sessions=_real_completed_sessions(db, participant.id),
        earned=_earned_coins(db, participant.id),
        display_name=_consent_display_name(db, participant.id),
    )


def _resolve_participant(db: Session, public_id: str) -> Participant:
    participant = db.execute(
        apply_participant_filter(select(Participant).where(Participant.public_id == public_id.upper()))
    ).scalar_one_or_none()
    if participant is None or is_synthetic_public_id(participant.public_id):
        raise GoldenVaultError("Participant not found", status_code=404)
    if not is_auto_session_eligible(participant):
        raise GoldenVaultError("Participant not found", status_code=404)
    return participant


def enable_override(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    if not row.random_seed:
        apply_profile_to_override(row, generate_demo_profile())
    row.enabled = True
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.override_enabled",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def disable_override(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    row.enabled = False
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.override_disabled",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def patch_override(db: Session, *, public_id: str, payload: dict[str, Any]) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    if payload.get("enabled") is True:
        if not row.random_seed:
            apply_profile_to_override(row, generate_demo_profile())
        row.enabled = True
    elif payload.get("enabled") is False:
        row.enabled = False
    if payload.get("bonus_sessions") is not None:
        row.bonus_sessions = max(0, int(payload["bonus_sessions"]))
    if payload.get("bonus_coins") is not None:
        row.bonus_coins = max(0, int(payload["bonus_coins"]))
    _touch(row)
    db.flush()
    db.refresh(row)
    return row


def adjust_sessions(
    db: Session,
    *,
    public_id: str,
    delta: int | None = None,
    set_to: int | None = None,
) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    before = int(row.bonus_sessions or 0)
    if set_to is not None:
        row.bonus_sessions = max(0, int(set_to))
    elif delta is not None:
        row.bonus_sessions = max(0, before + int(delta))
    if not row.enabled and row.bonus_sessions > 0:
        row.enabled = True
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.sessions_adjusted",
        participant_id=participant.id,
        metadata={
            "participant_public_id": participant.public_id,
            "before": before,
            "after": row.bonus_sessions,
            "delta": delta,
            "set_to": set_to,
        },
    )
    db.flush()
    db.refresh(row)
    return row


def add_bonus_sessions(db: Session, *, public_id: str, amount: int) -> GoldenDemoOverride:
    if amount < 1:
        raise GoldenVaultError("Amount must be at least 1", status_code=422)
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    before = int(row.bonus_sessions or 0)
    row.bonus_sessions = before + int(amount)
    if not row.enabled:
        row.enabled = True
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.sessions_manually_added",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id, "amount": amount, "before": before, "after": row.bonus_sessions},
    )
    db.flush()
    db.refresh(row)
    return row


def delete_bonus_sessions(db: Session, *, public_id: str, amount: int) -> GoldenDemoOverride:
    if amount < 1:
        raise GoldenVaultError("Amount must be at least 1", status_code=422)
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    before = int(row.bonus_sessions or 0)
    if amount > before:
        raise GoldenVaultError(
            f"Cannot remove {amount} bonus sessions; only {before} available.",
            status_code=422,
        )
    row.bonus_sessions = before - int(amount)
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.sessions_manually_deleted",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id, "amount": amount, "before": before, "after": row.bonus_sessions},
    )
    db.flush()
    db.refresh(row)
    return row


def adjust_coins(
    db: Session,
    *,
    public_id: str,
    delta: int | None = None,
    set_to: int | None = None,
) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    before = int(row.bonus_coins or 0)
    if set_to is not None:
        row.bonus_coins = max(0, int(set_to))
    elif delta is not None:
        row.bonus_coins = max(0, before + int(delta))
    if not row.enabled and row.bonus_coins > 0:
        row.enabled = True
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.coins_adjusted",
        participant_id=participant.id,
        metadata={
            "participant_public_id": participant.public_id,
            "before": before,
            "after": row.bonus_coins,
            "delta": delta,
            "set_to": set_to,
        },
    )
    db.flush()
    db.refresh(row)
    return row


def add_bonus_coins(db: Session, *, public_id: str, amount: int) -> GoldenDemoOverride:
    if amount < 1:
        raise GoldenVaultError("Amount must be at least 1", status_code=422)
    return adjust_coins(db, public_id=public_id, delta=amount)


def delete_bonus_coins(db: Session, *, public_id: str, amount: int) -> GoldenDemoOverride:
    if amount < 1:
        raise GoldenVaultError("Amount must be at least 1", status_code=422)
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    before = int(row.bonus_coins or 0)
    if amount > before:
        raise GoldenVaultError(
            f"Cannot remove {amount} bonus coins; only {before} available.",
            status_code=422,
        )
    row.bonus_coins = before - int(amount)
    if not row.enabled and row.bonus_coins > 0:
        row.enabled = True
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.coins_manually_deleted",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id, "amount": amount, "before": before, "after": row.bonus_coins},
    )
    db.flush()
    db.refresh(row)
    return row


def regenerate_metrics(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    apply_profile_to_override(row, generate_demo_profile())
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.metrics_regenerated",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def release_demo_feedback(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    if not row.simulated_feedback_headline:
        apply_profile_to_override(row, generate_demo_profile(seed=row.random_seed))
    row.simulated_feedback_status = "Released"
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.feedback_released",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def revoke_demo_feedback(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    row.simulated_feedback_status = "Revoked"
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.feedback_revoked",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def regenerate_demo_feedback(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    profile = generate_demo_profile(seed=row.random_seed)
    row.simulated_feedback_status = profile.get("simulated_feedback_status", "Released")
    row.simulated_feedback_level = profile.get("simulated_feedback_level")
    row.simulated_feedback_headline = profile.get("simulated_feedback_headline")
    row.simulated_feedback_summary = profile.get("simulated_feedback_summary")
    row.simulated_feedback_factors_json = profile.get("simulated_feedback_factors_json") or []
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.feedback_regenerated",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def reset_all_demo(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    row.enabled = False
    row.bonus_sessions = 0
    row.bonus_coins = 0
    row.simulated_reaction_ms = None
    row.simulated_stress = None
    row.simulated_fatigue = None
    row.simulated_sleep_hours = None
    row.simulated_memory_percent = None
    row.simulated_session_completion_percent = None
    row.simulated_feedback_status = None
    row.simulated_feedback_level = None
    row.simulated_feedback_headline = None
    row.simulated_feedback_summary = None
    row.simulated_feedback_factors_json = None
    row.last_active_minute_of_day = None
    row.random_seed = None
    row.auto_session_enabled = False
    row.next_auto_session_at = None
    row.last_auto_session_at = None
    row.last_auto_session_local_date = None
    row.auto_session_updated_at = None
    _touch(row)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.reset_all",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    db.refresh(row)
    return row


def _resolve_bulk_ids(
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
        items, _total = list_vault_participants(
            db,
            limit=500,
            offset=0,
            search=filter_payload.get("search"),
            golden_enabled=filter_payload.get("golden_enabled"),
            feedback_filter=filter_payload.get("feedback_filter"),
        )
        return [row["participantId"] for row in items if row["participantId"] not in excluded][:500]
    ids = []
    for value in participant_public_ids or []:
        pid = value.strip().upper()
        if pid and pid not in excluded:
            ids.append(pid)
    return ids[:500]


def set_auto_session_enabled(db: Session, *, public_id: str, enabled: bool) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    if enabled:
        enable_auto_session(db, row, participant)
    else:
        disable_auto_session(db, row, participant)
    _touch(row)
    db.flush()
    db.refresh(row)
    return row


def reschedule_auto_session_for_public_id(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    reschedule_auto_session(db, row, participant)
    _touch(row)
    db.flush()
    db.refresh(row)
    return row


def run_auto_session_now_for_public_id(db: Session, *, public_id: str) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    if not row.auto_session_enabled:
        raise GoldenVaultError("Auto Session is not enabled for this participant", status_code=400)
    awarded = run_auto_session_now(db, row, participant)
    if not awarded:
        raise GoldenVaultError("Automatic session already recorded for today", status_code=409)
    _touch(row)
    db.flush()
    db.refresh(row)
    return row


def run_bulk_action(db: Session, *, payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action") or ""
    ids = _resolve_bulk_ids(
        db,
        participant_public_ids=payload.get("participant_public_ids"),
        selection_mode=payload.get("selection_mode"),
        filters=payload.get("filters"),
        excluded_public_ids=payload.get("excluded_public_ids"),
    )
    result = {
        "requested_count": len(ids),
        "succeeded_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "failures": [],
    }
    amount = payload.get("amount")
    set_to = payload.get("set_to")

    handlers = {
        "enable": lambda pid: enable_override(db, public_id=pid),
        "disable": lambda pid: disable_override(db, public_id=pid),
        "add_sessions": lambda pid: add_bonus_sessions(db, public_id=pid, amount=int(amount or 0)),
        "delete_sessions": lambda pid: delete_bonus_sessions(db, public_id=pid, amount=int(amount or 0)),
        "subtract_sessions": lambda pid: delete_bonus_sessions(db, public_id=pid, amount=int(amount or 0)),
        "set_sessions": lambda pid: adjust_sessions(db, public_id=pid, set_to=int(set_to if set_to is not None else amount or 0)),
        "add_coins": lambda pid: add_bonus_coins(db, public_id=pid, amount=int(amount or 0)),
        "delete_coins": lambda pid: delete_bonus_coins(db, public_id=pid, amount=int(amount or 0)),
        "subtract_coins": lambda pid: delete_bonus_coins(db, public_id=pid, amount=int(amount or 0)),
        "set_coins": lambda pid: adjust_coins(db, public_id=pid, set_to=int(set_to if set_to is not None else amount or 0)),
        "regenerate_metrics": lambda pid: regenerate_metrics(db, public_id=pid),
        "release_feedback": lambda pid: release_demo_feedback(db, public_id=pid),
        "revoke_feedback": lambda pid: revoke_demo_feedback(db, public_id=pid),
        "reset_all": lambda pid: reset_all_demo(db, public_id=pid),
        "auto_session_enable": lambda pid: set_auto_session_enabled(db, public_id=pid, enabled=True),
        "auto_session_disable": lambda pid: set_auto_session_enabled(db, public_id=pid, enabled=False),
        "auto_session_reschedule": lambda pid: reschedule_auto_session_for_public_id(db, public_id=pid),
        "auto_session_run_now": lambda pid: run_auto_session_now_for_public_id(db, public_id=pid),
    }
    handler = handlers.get(action)
    if handler is None:
        raise GoldenVaultError("Unknown bulk action", status_code=422)

    for public_id in ids:
        try:
            handler(public_id)
            result["succeeded_count"] += 1
        except GoldenVaultError as exc:
            if exc.status_code == 404:
                result["skipped_count"] += 1
            else:
                result["failed_count"] += 1
                result["failures"].append({"participantId": public_id, "message": exc.message})
        except Exception as exc:
            result["failed_count"] += 1
            result["failures"].append({"participantId": public_id, "message": str(exc)})

    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.bulk_action",
        metadata={
            "action": action,
            "requested_count": result["requested_count"],
            "succeeded_count": result["succeeded_count"],
            "failed_count": result["failed_count"],
            "skipped_count": result["skipped_count"],
        },
    )
    db.flush()
    return result


def preview_auto_data_for_public_id(
    db: Session,
    *,
    public_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    from datetime import date as date_cls

    start = date_cls.fromisoformat(str(payload["start_date"]))
    end_raw = payload.get("end_date")
    end = date_cls.fromisoformat(str(end_raw)) if end_raw else None
    frequency = map_participant_frequency(payload.get("frequency") or participant.study_frequency)
    weekdays = payload.get("weekdays")
    real_sessions = _real_completed_sessions(db, participant.id)
    preview = compute_auto_data_preview(
        db,
        participant=participant,
        row=row,
        start_date=start,
        end_date=end,
        frequency=frequency,
        weekdays=weekdays,
        real_completed_sessions=real_sessions,
    )
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.auto_data_preview",
        participant_id=participant.id,
        metadata={"participant_public_id": participant.public_id},
    )
    db.flush()
    return preview


def apply_auto_data_for_public_id(
    db: Session,
    *,
    public_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    from datetime import date as date_cls

    start = date_cls.fromisoformat(str(payload["start_date"]))
    end_raw = payload.get("end_date")
    end = date_cls.fromisoformat(str(end_raw)) if end_raw else None
    frequency = map_participant_frequency(payload.get("frequency") or participant.study_frequency)
    weekdays = payload.get("weekdays")
    enable_future = payload.get("enable_future", True)
    apply_auto_data_config(
        db,
        participant=participant,
        row=row,
        start_date=start,
        end_date=end,
        frequency=frequency,
        weekdays=weekdays,
        enable_future=bool(enable_future),
    )
    batch = apply_backfill_batch(db, participant=participant, row=row)
    db.flush()
    db.refresh(row)
    return {"backfill": batch, "bonusSessions": row.bonus_sessions}


def apply_auto_data_backfill_continue(db: Session, *, public_id: str) -> dict[str, Any]:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    batch = apply_backfill_batch(db, participant=participant, row=row)
    db.flush()
    return batch


def patch_auto_data_schedule(
    db: Session,
    *,
    public_id: str,
    payload: dict[str, Any],
) -> GoldenDemoOverride:
    participant = _resolve_participant(db, public_id)
    row = _get_or_create_override(db, participant)
    if payload.get("paused") is True:
        pause_auto_data(db, row, participant)
    elif payload.get("paused") is False:
        resume_auto_data(db, row, participant)
    if any(k in payload for k in ("start_date", "end_date", "frequency", "weekdays")):
        from datetime import date as date_cls

        start = date_cls.fromisoformat(str(payload.get("start_date") or row.auto_data_start_date))
        end_raw = payload.get("end_date", row.auto_data_end_date)
        end = date_cls.fromisoformat(str(end_raw)) if end_raw else None
        frequency = map_participant_frequency(payload.get("frequency") or row.auto_data_frequency or participant.study_frequency)
        weekdays = payload.get("weekdays", row.auto_data_weekdays_json)
        apply_auto_data_config(
            db,
            participant=participant,
            row=row,
            start_date=start,
            end_date=end,
            frequency=frequency,
            weekdays=weekdays,
            enable_future=bool(row.auto_session_enabled),
        )
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.auto_data_schedule_updated",
            participant_id=participant.id,
            metadata={"participant_public_id": participant.public_id},
        )
    _touch(row)
    db.flush()
    db.refresh(row)
    return row


def list_recent_audit_events(db: Session, *, limit: int = 50) -> list[dict[str, Any]]:
    from app.models.audit_event import AuditEvent

    events = db.execute(
        select(AuditEvent)
        .where(
            or_(
                AuditEvent.actor_type == "golden_vault",
                AuditEvent.event_type.like("golden_vault.%"),
            )
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [
        {
            "event_type": event.event_type,
            "created_at": event.created_at.isoformat(),
            "metadata": event.metadata_json or {},
        }
        for event in events
    ]


def build_demo_dashboard_export_rows(db: Session) -> list[dict[str, Any]]:
    participants = db.execute(apply_participant_filter(select(Participant))).scalars().all()
    participants = [p for p in participants if not is_synthetic_public_id(p.public_id)]
    override_map = load_overrides_map(db, [p.id for p in participants])
    from app.services.golden_vault_display_service import resolve_participant_display_metrics

    rows = []
    for participant in participants:
        override = override_map.get(participant.id)
        if override is None or not override.enabled:
            continue
        real_sessions = _real_completed_sessions(db, participant.id)
        metrics = {
            "sessions_completed": real_sessions,
            "sessions_started": real_sessions,
            "status": "Active",
        }
        display = resolve_participant_display_metrics(
            participant=participant,
            real_metrics=metrics,
            golden_override=override,
        )
        rows.append(
            {
                "participant_id": participant.public_id,
                "is_simulated": True,
                "real_completed_sessions": real_sessions,
                "displayed_completed_sessions": display.get("displayedCompletedSessions"),
                "bonus_sessions": display.get("bonusSessions"),
                "display_status": display.get("displayStatus"),
                "real_status": display.get("realStatus"),
                "average_reaction_ms": display.get("averageReactionTimeMs"),
                "average_stress": display.get("averageStress"),
                "average_fatigue": display.get("averageFatigue"),
                "average_sleep_hours": display.get("averageSleepHours"),
                "average_memory_accuracy": display.get("averageMemoryAccuracy"),
                "session_completion_percent": display.get("sessionCompletion"),
                "feedback_status": display.get("feedbackStatus"),
            }
        )
    return rows
