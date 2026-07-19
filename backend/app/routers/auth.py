from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import (
    ParticipantLoginRequest,
    ParticipantRegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.auth_service import AuthError, login_participant, register_participant
from app.services.consent_service import ConsentError


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
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ConsentError as exc:
        raise _consent_http_error(exc) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: ParticipantLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        return login_participant(db, payload)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        ) from exc
