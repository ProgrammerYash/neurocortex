from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.participant import Participant
from app.models.researcher import Researcher
from app.services.participant_account_service import AccountError, assert_participant_access, clear_expired_suspension
from app.utils.security import decode_access_token

security = HTTPBearer()


def _decode_token(credentials: HTTPAuthorizationCredentials) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid or expired token", "error_code": "TOKEN_INVALID"},
        ) from exc


def _account_http_error(exc: AccountError) -> HTTPException:
    detail = {"message": exc.message, "error_code": exc.error_code}
    detail.update(exc.extra)
    return HTTPException(status_code=exc.status_code, detail=detail)


def get_current_participant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Participant:
    payload = _decode_token(credentials)

    if payload.get("role") != "participant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Participant access required", "error_code": "FORBIDDEN"},
        )

    participant_id = payload.get("sub")
    if not participant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token payload", "error_code": "TOKEN_INVALID"},
        )

    try:
        participant_uuid = UUID(str(participant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token payload", "error_code": "TOKEN_INVALID"},
        ) from exc

    participant = db.execute(
        select(Participant).where(Participant.id == participant_uuid)
    ).scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Participant not found", "error_code": "TOKEN_INVALID"},
        )

    clear_expired_suspension(participant, db=db)
    try:
        assert_participant_access(
            participant,
            token_auth_version=payload.get("auth_version"),
            allow_pin_change_only=False,
        )
    except AccountError as exc:
        raise _account_http_error(exc) from exc

    return participant


def get_current_participant_allow_pin_change(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Participant:
    payload = _decode_token(credentials)

    if payload.get("role") != "participant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Participant access required", "error_code": "FORBIDDEN"},
        )

    participant_id = payload.get("sub")
    if not participant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token payload", "error_code": "TOKEN_INVALID"},
        )

    try:
        participant_uuid = UUID(str(participant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid token payload", "error_code": "TOKEN_INVALID"},
        ) from exc

    participant = db.execute(
        select(Participant).where(Participant.id == participant_uuid)
    ).scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Participant not found", "error_code": "TOKEN_INVALID"},
        )

    clear_expired_suspension(participant, db=db)
    try:
        assert_participant_access(
            participant,
            token_auth_version=payload.get("auth_version"),
            allow_pin_change_only=True,
        )
    except AccountError as exc:
        raise _account_http_error(exc) from exc

    return participant


def get_current_researcher(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Researcher:
    payload = _decode_token(credentials)

    if payload.get("role") != "researcher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Researcher access required",
        )

    researcher_id = payload.get("sub")
    if not researcher_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        researcher_uuid = UUID(str(researcher_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc

    researcher = db.execute(
        select(Researcher).where(Researcher.id == researcher_uuid)
    ).scalar_one_or_none()
    if researcher is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Researcher not found",
        )

    return researcher
