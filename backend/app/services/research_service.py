from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import DailySession
from app.models.module_result import ModuleResult
from app.models.participant import Participant
from app.schemas.research import ResearchStatsResponse
from app.schemas.session import CORE_MODULE_KEYS
from app.services.session_service import serialize_session
from app.services.study_guard import apply_participant_filter, is_synthetic_public_id


def list_research_participants(db: Session) -> list[dict[str, object]]:
    query = apply_participant_filter(
        select(Participant).order_by(Participant.created_at.asc())
    )
    participants = db.execute(query).scalars().all()
    return [
        {
            "id": participant.public_id,
            "role": "participant",
            "grade": participant.grade,
            "ageRange": participant.age_range,
            "petChoice": participant.pet_choice,
            "joinedDate": participant.created_at.date().isoformat(),
            "joinedAt": int(participant.created_at.timestamp() * 1000),
        }
        for participant in participants
    ]


def list_research_sessions(db: Session) -> list[dict[str, object]]:
    query = (
        select(DailySession)
        .options(
            selectinload(DailySession.module_results),
            selectinload(DailySession.participant),
        )
        .join(Participant, DailySession.participant_id == Participant.id)
        .order_by(DailySession.session_date.asc())
    )
    query = apply_participant_filter(query)
    sessions = db.execute(query).scalars().all()

    rows: list[dict[str, object]] = []
    for session in sessions:
        participant = session.participant
        if is_synthetic_public_id(participant.public_id):
            continue
        record = serialize_session(session, participant.public_id)
        record["participantID"] = participant.public_id
        record["grade"] = participant.grade
        record["ageRange"] = participant.age_range
        record["joinedDate"] = participant.created_at.date().isoformat()
        rows.append(record)
    return rows


def get_research_stats(db: Session) -> ResearchStatsResponse:
    participant_query = apply_participant_filter(select(func.count()).select_from(Participant))
    total_participants = db.execute(participant_query).scalar_one()

    session_query = (
        select(func.count())
        .select_from(DailySession)
        .join(Participant, DailySession.participant_id == Participant.id)
    )
    session_query = apply_participant_filter(session_query)
    total_sessions = db.execute(session_query).scalar_one()

    complete_query = (
        select(func.count())
        .select_from(DailySession)
        .join(Participant, DailySession.participant_id == Participant.id)
        .where(DailySession.complete.is_(True))
    )
    complete_query = apply_participant_filter(complete_query)
    complete_sessions = db.execute(complete_query).scalar_one()

    module_query = (
        select(func.count())
        .select_from(ModuleResult)
        .join(DailySession, ModuleResult.session_id == DailySession.id)
        .join(Participant, DailySession.participant_id == Participant.id)
    )
    module_query = apply_participant_filter(module_query)
    total_module_results = db.execute(module_query).scalar_one()

    completion_rate = (
        (complete_sessions / total_sessions) * 100 if total_sessions else 0.0
    )
    module_slots = total_sessions * len(CORE_MODULE_KEYS) if total_sessions else 0
    average_module_completion = (
        (total_module_results / module_slots) * 100 if module_slots else 0.0
    )

    return ResearchStatsResponse(
        total_participants=total_participants,
        total_sessions=total_sessions,
        completion_rate=round(completion_rate, 1),
        average_module_completion=round(average_module_completion, 1),
    )
