from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_participant_allow_pin_change
from app.models.participant import Participant
from app.schemas.auth import (
    ChangePinRequest,
    ParticipantLoginRequest,
    ParticipantRegisterRequest,
    RecentParticipantStatusRequest,
    RecentParticipantStatusResponse,
    RecentParticipantStatusItem,
    RegisterResponse,
    TokenResponse,
)
from app.services.auth_service import (
    AuthError,
    complete_pin_change,
    login_participant,
    recent_participant_status,
    register_participant,
)
from app.services.consent_service import ConsentError


def _auth_http_error(exc: AuthError) -> HTTPException:
    detail = {"message": exc.message}
    if exc.error_code:
        detail["error_code"] = exc.error_code
    detail.update(exc.extra)
    return HTTPException(status_code=exc.status_code, detail=detail)


def _consent_http_error(exc: ConsentError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"message": exc.message, "error_code": exc.error_code},
    )


router = APIRouter(prefix="/auth/participant", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: ParticipantRegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    try:
        return register_participant(db, payload)
    except AuthError as exc:
        raise _auth_http_error(exc) from exc
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from exc


@router.post("/recent-status", response_model=RecentParticipantStatusResponse)
def participant_recent_status(
    payload: RecentParticipantStatusRequest,
    db: Session = Depends(get_db),
) -> RecentParticipantStatusResponse:
    items = recent_participant_status(db, payload.public_ids)
    return RecentParticipantStatusResponse(
        participants=[RecentParticipantStatusItem(**item) for item in items]
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: ParticipantLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return login_participant(db, payload)
    except AuthError as exc:
        raise _auth_http_error(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        ) from exc


@router.post("/change-pin", response_model=TokenResponse)
def change_pin(
    payload: ChangePinRequest,
    participant: Participant = Depends(get_current_participant_allow_pin_change),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not participant.must_change_pin:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "PIN change is not required.", "error_code": "PIN_CHANGE_NOT_REQUIRED"},
        )
    try:
        return complete_pin_change(db, participant, payload)
    except AuthError as exc:
        raise _auth_http_error(exc) from exc
