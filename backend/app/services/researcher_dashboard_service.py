"""Researcher participant dashboard summaries and paginated roster metrics."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.consent_record import ConsentRecord
from app.models.daily_session import DailySession
from app.models.participant import Participant
from app.models.participant_consent_event import ParticipantConsentEvent
from app.schemas.session import CORE_MODULE_KEYS
from app.services.consent_content import CONSENT_VERSION
from app.services.consent_service import WITHDRAWAL_EVENT_TYPES
from app.services.participant_account_service import (
    account_state_payload,
    matches_status_filter,
    resolve_display_status,
)
from app.services.data_quality_service import IMPOSSIBLE_REACTION_MS
from app.services.study_guard import apply_participant_filter, is_synthetic_public_id

STUDY_TIMEZONE = ZoneInfo("America/New_York")
CORE_MODULES = tuple(CORE_MODULE_KEYS)
SORT_FIELDS = frozenset(
    {
        "participant_id",
        "joined",
        "sessions",
        "last_active",
        "status",
        "average_reaction_time",
        "average_stress",
        "average_fatigue",
        "average_sleep",
        "average_memory_accuracy",
        "session_completion",
        "student_name",
        "guardian_name",
    }
)
STATUS_ORDER = {"Removed": 0, "Disabled": 1, "Suspended": 2, "Withdrawn": 3, "Active": 4, "Inactive": 5}


def format_study_date(value: datetime | date) -> str:
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(STUDY_TIMEZONE).strftime("%b %d, %Y")


def format_study_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    local = value.astimezone(STUDY_TIMEZONE)
    return local.strftime("%b %d, %Y %I:%M %p").lstrip("0").replace(" 0", " ")


def _safe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _round_metric(value: float | None, places: int = 1) -> float | None:
    if value is None:
        return None
    return round(value, places)


def _reaction_excluded(session: DailySession, payload: dict[str, Any]) -> bool:
    for flag in session.data_quality_flags:
        if flag.module_key != "reaction":
            continue
        if flag.review_status == "reviewed_exclude":
            return True
        if (
            flag.flag_type == "impossible_reaction_time"
            and flag.review_status == "unresolved"
            and flag.severity == "critical"
        ):
            return True
    try:
        avg = float(payload.get("avg"))
    except (TypeError, ValueError):
        return True
    return avg <= 0 or avg < IMPOSSIBLE_REACTION_MS


def _valid_reaction_avg(payload: dict[str, Any]) -> float | None:
    try:
        avg = float(payload.get("avg"))
    except (TypeError, ValueError):
        return None
    if avg <= 0 or avg < IMPOSSIBLE_REACTION_MS:
        return None
    return avg


def _valid_survey_value(payload: dict[str, Any], key: str) -> float | None:
    try:
        value = float(payload.get(key))
    except (TypeError, ValueError):
        return None
    if key in {"stress", "fatigue", "motivation", "mood", "socialStress"} and not 1 <= value <= 10:
        return None
    if key == "sleep" and not 0 <= value <= 12:
        return None
    return value


def _valid_memory_accuracy(payload: dict[str, Any]) -> float | None:
    try:
        value = float(payload.get("accuracy"))
    except (TypeError, ValueError):
        return None
    if value < 0 or value > 100:
        return None
    return value


def _aggregate_sessions(sessions: list[DailySession]) -> dict[str, Any]:
    by_date: dict[date, dict[str, Any]] = defaultdict(
        lambda: {
            "modules": set(),
            "payloads": {},
            "last_active": None,
            "sessions": [],
        }
    )
    reaction_values: list[float] = []
    stress_values: list[float] = []
    fatigue_values: list[float] = []
    sleep_values: list[float] = []
    memory_values: list[float] = []

    for session in sessions:
        entry = by_date[session.session_date]
        entry["sessions"].append(session)
        for result in session.module_results:
            entry["modules"].add(result.module_key)
            entry["payloads"][result.module_key] = result.payload
            recorded_at = result.recorded_at
            if entry["last_active"] is None or recorded_at > entry["last_active"]:
                entry["last_active"] = recorded_at

            if result.module_key == "reaction" and not _reaction_excluded(session, result.payload):
                reaction = _valid_reaction_avg(result.payload)
                if reaction is not None:
                    reaction_values.append(reaction)
            elif result.module_key == "survey":
                stress = _valid_survey_value(result.payload, "stress")
                fatigue = _valid_survey_value(result.payload, "fatigue")
                sleep = _valid_survey_value(result.payload, "sleep")
                if stress is not None:
                    stress_values.append(stress)
                if fatigue is not None:
                    fatigue_values.append(fatigue)
                if sleep is not None:
                    sleep_values.append(sleep)
            elif result.module_key == "memory":
                accuracy = _valid_memory_accuracy(result.payload)
                if accuracy is not None:
                    memory_values.append(accuracy)

    started_dates = [session_date for session_date, entry in by_date.items() if entry["modules"]]
    completed_dates = [
        session_date
        for session_date, entry in by_date.items()
        if entry["modules"] and CORE_MODULE_KEYS.issubset(entry["modules"])
    ]
    last_active = None
    for entry in by_date.values():
        if entry["last_active"] and (last_active is None or entry["last_active"] > last_active):
            last_active = entry["last_active"]

    session_completion = None
    if started_dates:
        session_completion = round(len(completed_dates) / len(started_dates) * 100, 1)

    history = []
    for session_date in sorted(by_date.keys(), reverse=True):
        entry = by_date[session_date]
        modules = entry["modules"]
        history.append(
            {
                "date": session_date.isoformat(),
                "reaction_completed": "reaction" in modules,
                "typing_completed": "typing" in modules,
                "memory_completed": "memory" in modules,
                "attention_completed": "attention" in modules,
                "survey_completed": "survey" in modules,
                "complete": CORE_MODULE_KEYS.issubset(modules),
            }
        )

    return {
        "sessions_started": len(started_dates),
        "sessions_completed": len(completed_dates),
        "session_completion": session_completion,
        "last_active_at": last_active,
        "average_reaction_time_ms": _round_metric(_safe_mean(reaction_values), 0),
        "average_stress": _round_metric(_safe_mean(stress_values), 1),
        "average_fatigue": _round_metric(_safe_mean(fatigue_values), 1),
        "average_sleep_hours": _round_metric(_safe_mean(sleep_values), 1),
        "average_memory_accuracy": _round_metric(_safe_mean(memory_values), 1),
        "history": history,
        "global_reaction_values": reaction_values,
        "global_stress_values": stress_values,
        "global_fatigue_values": fatigue_values,
        "global_sleep_values": sleep_values,
        "global_memory_values": memory_values,
        "global_started_dates": len(started_dates),
        "global_completed_dates": len(completed_dates),
    }


def _load_consent_names(db: Session, participant_ids: list[UUID]) -> dict[UUID, ConsentRecord | None]:
    if not participant_ids:
        return {}
    records = db.execute(
        select(ConsentRecord).where(
            ConsentRecord.participant_id.in_(participant_ids),
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
    ).scalars().all()
    return {record.participant_id: record for record in records}


def _load_withdrawal_statuses(db: Session, participant_ids: list[UUID]) -> dict[UUID, str]:
    if not participant_ids:
        return {}
    events = db.execute(
        select(ParticipantConsentEvent)
        .where(
            ParticipantConsentEvent.participant_id.in_(participant_ids),
            ParticipantConsentEvent.event_type.in_(WITHDRAWAL_EVENT_TYPES),
        )
        .order_by(
            ParticipantConsentEvent.created_at.asc(),
            ParticipantConsentEvent.id.asc(),
        )
    ).scalars().all()
    statuses: dict[UUID, str] = {}
    for event in events:
        statuses[event.participant_id] = event.status or event.event_type
    return statuses


def _load_sessions_by_participant(db: Session, participant_ids: list[UUID]) -> dict[UUID, list[DailySession]]:
    if not participant_ids:
        return {}
    sessions = db.execute(
        select(DailySession)
        .options(
            selectinload(DailySession.module_results),
            selectinload(DailySession.data_quality_flags),
        )
        .where(DailySession.participant_id.in_(participant_ids))
        .order_by(DailySession.session_date.asc(), DailySession.session_slot.asc())
    ).scalars().all()
    grouped: dict[UUID, list[DailySession]] = defaultdict(list)
    for session in sessions:
        grouped[session.participant_id].append(session)
    return grouped


def _participant_status(
    participant: Participant,
    *,
    withdrawal_status: str | None,
    last_active_at: datetime | None,
    sessions_started: int,
) -> str:
    return resolve_display_status(
        participant,
        withdrawal_status=withdrawal_status,
        last_active_at=last_active_at,
        sessions_started=sessions_started,
    )


def _base_participant_query(db: Session, search: str | None):
    query = apply_participant_filter(select(Participant))
    if search and search.strip():
        term = f"%{search.strip()}%"
        consent_match = (
            select(ConsentRecord.participant_id)
            .where(
                ConsentRecord.consent_version == CONSENT_VERSION,
                ConsentRecord.revoked_at.is_(None),
                or_(
                    ConsentRecord.participant_printed_name.ilike(term),
                    ConsentRecord.guardian_printed_name.ilike(term),
                ),
            )
            .subquery()
        )
        query = query.where(
            or_(
                Participant.public_id.ilike(term),
                Participant.id.in_(select(consent_match.c.participant_id)),
            )
        )
    return query.order_by(Participant.created_at.asc())


def _build_participant_row(
    participant: Participant,
    *,
    consent: ConsentRecord | None,
    withdrawal_status: str | None,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    student_name = consent.participant_printed_name if consent else None
    guardian_name = consent.guardian_printed_name if consent else None
    status = _participant_status(
        participant,
        withdrawal_status=withdrawal_status,
        last_active_at=metrics["last_active_at"],
        sessions_started=metrics["sessions_started"],
    )
    last_active_at = metrics["last_active_at"]
    return {
        "participantId": participant.public_id,
        "studentName": student_name,
        "guardianName": guardian_name,
        "grade": participant.grade,
        "ageRange": participant.age_range,
        "joinedAt": participant.created_at,
        "joinedDisplay": format_study_date(participant.created_at),
        "sessions": metrics["sessions_started"],
        "lastActiveAt": last_active_at,
        "lastActiveDisplay": format_study_datetime(last_active_at),
        "status": status,
        "averageReactionTimeMs": metrics["average_reaction_time_ms"],
        "averageStress": metrics["average_stress"],
        "averageFatigue": metrics["average_fatigue"],
        "averageSleepHours": metrics["average_sleep_hours"],
        "averageMemoryAccuracy": metrics["average_memory_accuracy"],
        "sessionCompletion": metrics["session_completion"],
        "_metrics": metrics,
    }


def _sort_rows(rows: list[dict[str, Any]], sort: str, direction: str) -> list[dict[str, Any]]:
    reverse = direction == "desc"

    def sort_key(row: dict[str, Any]):
        if sort == "participant_id":
            return row["participantId"]
        if sort == "student_name":
            return (row["studentName"] or "").lower()
        if sort == "guardian_name":
            return (row["guardianName"] or "").lower()
        if sort == "joined":
            return row["joinedAt"]
        if sort == "sessions":
            return row["sessions"]
        if sort == "last_active":
            return row["lastActiveAt"] or datetime.min.replace(tzinfo=UTC)
        if sort == "status":
            return STATUS_ORDER.get(row["status"], 99)
        if sort == "average_reaction_time":
            return row["averageReactionTimeMs"] if row["averageReactionTimeMs"] is not None else -1
        if sort == "average_stress":
            return row["averageStress"] if row["averageStress"] is not None else -1
        if sort == "average_fatigue":
            return row["averageFatigue"] if row["averageFatigue"] is not None else -1
        if sort == "average_sleep":
            return row["averageSleepHours"] if row["averageSleepHours"] is not None else -1
        if sort == "average_memory_accuracy":
            return row["averageMemoryAccuracy"] if row["averageMemoryAccuracy"] is not None else -1
        if sort == "session_completion":
            return row["sessionCompletion"] if row["sessionCompletion"] is not None else -1
        return row["joinedAt"]

    return sorted(rows, key=sort_key, reverse=reverse)


def _compute_rows(db: Session, participants: list[Participant]) -> list[dict[str, Any]]:
    participant_ids = [participant.id for participant in participants if not is_synthetic_public_id(participant.public_id)]
    participants = [participant for participant in participants if participant.id in participant_ids]
    if not participants:
        return []

    ids = [participant.id for participant in participants]
    consent_map = _load_consent_names(db, ids)
    withdrawal_map = _load_withdrawal_statuses(db, ids)
    sessions_map = _load_sessions_by_participant(db, ids)

    rows = []
    for participant in participants:
        metrics = _aggregate_sessions(sessions_map.get(participant.id, []))
        rows.append(
            _build_participant_row(
                participant,
                consent=consent_map.get(participant.id),
                withdrawal_status=withdrawal_map.get(participant.id),
                metrics=metrics,
            )
        )
    return rows


def _summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reaction_values: list[float] = []
    stress_values: list[float] = []
    fatigue_values: list[float] = []
    sleep_values: list[float] = []
    memory_values: list[float] = []
    started_total = 0
    completed_total = 0
    active_ids: set[str] = set()
    now = datetime.now(UTC)

    for row in rows:
        metrics = row["_metrics"]
        reaction_values.extend(metrics["global_reaction_values"])
        stress_values.extend(metrics["global_stress_values"])
        fatigue_values.extend(metrics["global_fatigue_values"])
        sleep_values.extend(metrics["global_sleep_values"])
        memory_values.extend(metrics["global_memory_values"])
        started_total += metrics["global_started_dates"]
        completed_total += metrics["global_completed_dates"]
        last_active = metrics["last_active_at"]
        if last_active is not None:
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=UTC)
            if now - last_active <= timedelta(days=7):
                active_ids.add(row["participantId"])

    completion = None
    if started_total:
        completion = round(completed_total / started_total * 100, 1)

    return {
        "totalParticipants": len(rows),
        "totalSessions": started_total,
        "activeParticipants7d": len(active_ids),
        "averageSessionCompletion": completion,
        "averageReactionTimeMs": _round_metric(_safe_mean(reaction_values), 0),
        "averageStress": _round_metric(_safe_mean(stress_values), 1),
        "averageFatigue": _round_metric(_safe_mean(fatigue_values), 1),
        "averageSleepHours": _round_metric(_safe_mean(sleep_values), 1),
        "averageMemoryAccuracy": _round_metric(_safe_mean(memory_values), 1),
    }


def _strip_internal(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "_metrics"}


def get_dashboard_summary(db: Session) -> dict[str, Any]:
    participants = db.execute(_base_participant_query(db, None)).scalars().all()
    rows = _compute_rows(db, participants)
    visible_rows = [row for row in rows if row["status"] != "Removed"]
    return _summary_from_rows(visible_rows)


def list_dashboard_participants(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None,
    sort: str,
    direction: str,
    status_filter: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    if sort not in SORT_FIELDS:
        sort = "joined"
    if direction not in {"asc", "desc"}:
        direction = "desc"

    participants = db.execute(_base_participant_query(db, search)).scalars().all()
    rows = [_strip_internal(row) for row in _sort_rows(_compute_rows(db, participants), sort, direction)]
    if status_filter:
        rows = [row for row in rows if matches_status_filter(row["status"], status_filter)]
    else:
        rows = [row for row in rows if matches_status_filter(row["status"], "all_current")]
    total = len(rows)
    page = rows[offset : offset + limit]
    return page, total


def get_dashboard_participant_detail(db: Session, public_id: str) -> dict[str, Any] | None:
    participant = db.execute(
        apply_participant_filter(select(Participant).where(Participant.public_id == public_id))
    ).scalar_one_or_none()
    if participant is None or is_synthetic_public_id(participant.public_id):
        return None

    rows = _compute_rows(db, [participant])
    if not rows:
        return None
    row = _strip_internal(rows[0])
    metrics = rows[0]["_metrics"]
    account = account_state_payload(participant)
    return {
        **row,
        **account,
        "sessionsStarted": metrics["sessions_started"],
        "sessionsCompleted": metrics["sessions_completed"],
        "recentSessions": [
            {
                "date": entry["date"],
                "reactionCompleted": entry["reaction_completed"],
                "typingCompleted": entry["typing_completed"],
                "memoryCompleted": entry["memory_completed"],
                "attentionCompleted": entry["attention_completed"],
                "surveyCompleted": entry["survey_completed"],
                "complete": entry["complete"],
            }
            for entry in metrics["history"][:14]
        ],
    }
