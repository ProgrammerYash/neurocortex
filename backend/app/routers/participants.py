from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_participant
from app.models.participant import Participant
from app.schemas.game import GameDataPayload
from app.schemas.consent import ConsentStatusResponse, ParticipantConsentSubmitRequest
from app.schemas.participant import ParticipantMeResponse
from app.schemas.session import DailySessionRecord, ModuleUpsertRequest, VALID_MODULE_KEYS
from app.services.game_service import GameDataError, get_participant_game_data, upsert_participant_game_data
from app.services.consent_service import (
    ConsentError,
    build_consent_status,
    record_deletion_request,
    record_withdrawal,
    session_block_message,
)
from app.services.electronic_consent_service import (
    complete_existing_participant_consent,
    has_current_consent,
)
from app.services.procedure_service import build_participant_study_progress
from app.services.session_service import (
    SessionError,
    abandon_session,
    get_today_session,
    list_participant_sessions,
    upsert_module_result,
)
from app.schemas.procedure import ParticipantStudyProgressResponse

router = APIRouter(prefix="/participants", tags=["participants"])


def _consent_http_error(exc: ConsentError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"message": exc.message, "error_code": exc.error_code},
    )


@router.get("/me/consent-status", response_model=ConsentStatusResponse)
def get_my_consent_status(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        return build_consent_status(db, participant)
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc


@router.post("/me/consent", response_model=ConsentStatusResponse)
def submit_my_consent(
    payload: ParticipantConsentSubmitRequest,
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        return complete_existing_participant_consent(
            db,
            participant=participant,
            payload=payload.model_dump(),
        )
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc


@router.post("/me/withdraw", response_model=ConsentStatusResponse)
def withdraw_my_participation(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        return record_withdrawal(db, participant=participant)
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc


@router.post("/me/request-data-deletion", response_model=ConsentStatusResponse)
def request_my_data_deletion(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        return record_deletion_request(db, participant=participant)
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc


@router.get("/me", response_model=ParticipantMeResponse)
def get_me(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> ParticipantMeResponse:
    return ParticipantMeResponse.from_participant(
        participant,
        consent_recorded=has_current_consent(db, participant.id),
    )


@router.get("/me/sessions", response_model=list[DailySessionRecord])
def get_my_sessions(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_participant_sessions(db, participant)


@router.get("/me/study-progress", response_model=ParticipantStudyProgressResponse)
def get_my_study_progress(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> ParticipantStudyProgressResponse:
    try:
        consent = build_consent_status(db, participant)
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc
    from app.services.session_service import today_session_date

    progress = build_participant_study_progress(
        db,
        participant_id=participant.id,
        session_date=today_session_date(),
        consent_eligible=consent["session_eligible"],
        consent_block_reason=consent.get("session_block_reason"),
        consent_block_message=consent.get("session_block_message"),
        withdrawal_status=consent.get("withdrawal_status", "active"),
    )
    return ParticipantStudyProgressResponse(**progress)


@router.post("/me/sessions/{session_date}/abandon", response_model=DailySessionRecord)
def abandon_my_session(
    session_date: date,
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return abandon_session(db, participant, session_date)
    except SessionError as exc:
        detail = {"message": exc.message}
        if exc.error_code:
            detail["error_code"] = exc.error_code
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc


@router.get("/me/sessions/today", response_model=DailySessionRecord | None)
def get_my_today_session(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object] | None:
    return get_today_session(db, participant)


@router.put(
    "/me/sessions/{session_date}/modules/{module_key}",
    response_model=DailySessionRecord,
)
def upsert_my_module_result(
    session_date: date,
    module_key: str,
    payload: ModuleUpsertRequest,
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if module_key not in VALID_MODULE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"module_key must be one of: {', '.join(sorted(VALID_MODULE_KEYS))}",
        )
    try:
        return upsert_module_result(
            db,
            participant,
            session_date,
            module_key,
            payload.payload,
        )
    except SessionError as exc:
        detail = {"message": exc.message}
        if exc.error_code:
            detail["error_code"] = exc.error_code
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save module result",
        ) from exc


@router.get("/me/game", response_model=GameDataPayload | None)
def get_my_game(
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict | None:
    return get_participant_game_data(db, participant)


@router.put("/me/game", response_model=GameDataPayload)
def upsert_my_game(
    payload: GameDataPayload,
    participant: Participant = Depends(get_current_participant),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return upsert_participant_game_data(db, participant, payload.model_dump())
    except GameDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save game data",
        ) from exc
