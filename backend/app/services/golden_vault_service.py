"""Golden Vault demo override persistence and admin operations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.models.participant_game_data import ParticipantGameData
from app.services.audit_service import record_audit_event
from app.services.consent_content import CONSENT_VERSION
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


def _earned_coins(db: Session, participant_id: UUID) -> int:
    row = db.execute(
        select(ParticipantGameData).where(ParticipantGameData.participant_id == participant_id)
    ).scalar_one_or_none()
    if row is None:
        return 0
    return int((row.game_data or {}).get("coins") or 0)


def _real_completed_sessions(db: Session, participant_id: UUID) -> int:
    sessions = _load_sessions_by_participant(db, [participant_id]).get(participant_id, [])
    return int(_aggregate_sessions(sessions)["sessions_completed"])


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
    db: Session,
    participant: Participant,
    override: GoldenDemoOverride | None,
) -> dict[str, Any]:
    real_sessions = _real_completed_sessions(db, participant.id)
    earned = _earned_coins(db, participant.id)
    enabled = bool(override and override.enabled)
    bonus_sessions = max(0, int(override.bonus_sessions or 0)) if override else 0
    bonus_coins = max(0, int(override.bonus_coins or 0)) if override else 0
    return {
        "participantId": participant.public_id,
        "displayName": _consent_display_name(db, participant.id),
        "enabled": enabled,
        "realCompletedSessions": real_sessions,
        "bonusSessions": bonus_sessions,
        "displayedCompletedSessions": real_sessions + (bonus_sessions if enabled else 0),
        "earnedCoins": earned,
        "bonusCoins": bonus_coins if enabled else 0,
        "displayedCoins": earned + (bonus_coins if enabled else 0),
        "feedbackLevel": override.simulated_feedback_level if override else None,
        "feedbackStatus": override.simulated_feedback_status if override else None,
        "updatedAt": override.updated_at.isoformat() if override and override.updated_at else None,
    }


def list_vault_participants(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None,
    golden_enabled: str | None,
    feedback_filter: str | None,
) -> tuple[list[dict[str, Any]], int]:
    query = apply_participant_filter(select(Participant))
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(Participant.public_id.ilike(term))
    participants = db.execute(query.order_by(Participant.created_at.asc())).scalars().all()
    participants = [p for p in participants if not is_synthetic_public_id(p.public_id)]
    override_map = load_overrides_map(db, [p.id for p in participants])
    rows = []
    for participant in participants:
        override = override_map.get(participant.id)
        row = _participant_row_payload(db, participant, override)
        if golden_enabled == "enabled" and not row["enabled"]:
            continue
        if golden_enabled == "disabled" and row["enabled"]:
            continue
        if feedback_filter == "released" and row.get("feedbackStatus") != "Released":
            continue
        if feedback_filter == "revoked" and row.get("feedbackStatus") != "Revoked":
            continue
        rows.append(row)
    total = len(rows)
    return rows[offset : offset + limit], total


def get_vault_participant(db: Session, public_id: str) -> dict[str, Any] | None:
    participant = db.execute(
        apply_participant_filter(select(Participant).where(Participant.public_id == public_id.upper()))
    ).scalar_one_or_none()
    if participant is None or is_synthetic_public_id(participant.public_id):
        return None
    override = get_override_for_participant(db, participant.id)
    return _participant_row_payload(db, participant, override)


def _resolve_participant(db: Session, public_id: str) -> Participant:
    participant = db.execute(
        apply_participant_filter(select(Participant).where(Participant.public_id == public_id.upper()))
    ).scalar_one_or_none()
    if participant is None or is_synthetic_public_id(participant.public_id):
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
        "add_sessions": lambda pid: adjust_sessions(db, public_id=pid, delta=int(amount or 0)),
        "subtract_sessions": lambda pid: adjust_sessions(db, public_id=pid, delta=-int(amount or 0)),
        "set_sessions": lambda pid: adjust_sessions(db, public_id=pid, set_to=int(set_to if set_to is not None else amount or 0)),
        "add_coins": lambda pid: adjust_coins(db, public_id=pid, delta=int(amount or 0)),
        "subtract_coins": lambda pid: adjust_coins(db, public_id=pid, delta=-int(amount or 0)),
        "set_coins": lambda pid: adjust_coins(db, public_id=pid, set_to=int(set_to if set_to is not None else amount or 0)),
        "regenerate_metrics": lambda pid: regenerate_metrics(db, public_id=pid),
        "release_feedback": lambda pid: release_demo_feedback(db, public_id=pid),
        "revoke_feedback": lambda pid: revoke_demo_feedback(db, public_id=pid),
        "reset_all": lambda pid: reset_all_demo(db, public_id=pid),
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
