from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.participant import Participant
from app.schemas.auth import (
    ChangePinRequest,
    ParticipantLoginRequest,
    ParticipantRegisterRequest,
    ParticipantProfile,
    RegisterResponse,
    TokenResponse,
)
from app.services.participant_account_service import AccountError, assert_login_allowed, change_participant_pin
from app.utils.ids import generate_public_id
from app.utils.security import create_access_token, hash_pin, verify_pin


class AuthError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str | None = None,
        extra: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.extra = extra or {}
        super().__init__(message)


def register_participant(db: Session, payload: ParticipantRegisterRequest) -> RegisterResponse:
    from app.services.consent_service import validate_registration_consent_category_for_age
    from app.services.electronic_consent_service import create_consent_record_uncommitted

    idempotency_key = str(payload.idempotency_key)
    replay = db.execute(
        select(ConsentRecord).where(ConsentRecord.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if replay is not None:
        participant = db.get(Participant, replay.participant_id)
        if participant is None or not verify_pin(payload.pin, participant.pin_hash):
            raise AuthError("Idempotency key has already been used", status_code=409)
        return _register_response(participant)

    consent_category = validate_registration_consent_category_for_age(
        payload.age,
        payload.age_consent_category,
    )
    public_id = _unique_public_id(db)
    participant = Participant(
        public_id=public_id,
        pin_hash=hash_pin(payload.pin),
        grade=payload.grade,
        age_range=str(payload.age),
        age_years=payload.age,
        age_consent_category=consent_category,
        pet_choice=payload.pet_choice,
    )
    try:
        db.add(participant)
        db.flush()
        create_consent_record_uncommitted(
            db,
            participant=participant,
            payload=payload.model_dump(),
        )
        db.commit()
        db.refresh(participant)
    except IntegrityError as exc:
        db.rollback()
        replay = db.execute(
            select(ConsentRecord).where(ConsentRecord.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if replay is not None:
            existing_participant = db.get(Participant, replay.participant_id)
            if existing_participant is not None and verify_pin(
                payload.pin,
                existing_participant.pin_hash,
            ):
                return _register_response(existing_participant)
        raise AuthError("Registration conflicts with an existing record", status_code=409) from exc
    except Exception:
        db.rollback()
        raise

    return _register_response(participant)


def _register_response(participant: Participant) -> RegisterResponse:
    token = create_access_token(
        participant_id=participant.id,
        public_id=participant.public_id,
        auth_version=participant.auth_version,
    )
    return RegisterResponse(
        access_token=token,
        public_id=participant.public_id,
        must_change_pin=participant.must_change_pin,
        participant=ParticipantProfile(
            public_id=participant.public_id,
            grade=participant.grade,
            age_range=participant.age_range,
            age_consent_category=participant.age_consent_category,
            pet_choice=participant.pet_choice,
        ),
    )


def recent_participant_status(db: Session, public_ids: list[str]) -> list[dict[str, object]]:
    if not public_ids:
        return []
    rows = db.execute(
        select(Participant.public_id, Participant.removed_at).where(
            Participant.public_id.in_(public_ids)
        )
    ).all()
    by_id = {public_id: removed_at for public_id, removed_at in rows}
    return [
        {
            "public_id": pid,
            "recent_eligible": pid in by_id and by_id[pid] is None,
        }
        for pid in public_ids
    ]


def login_participant(db: Session, payload: ParticipantLoginRequest) -> TokenResponse:
    participant = db.execute(
        select(Participant).where(Participant.public_id == payload.public_id)
    ).scalar_one_or_none()
    if participant is None or not verify_pin(payload.pin, participant.pin_hash):
        raise AuthError("Invalid public ID or PIN", status_code=401)

    try:
        assert_login_allowed(participant)
    except AccountError as exc:
        raise AuthError(
            exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            extra=exc.extra,
        ) from exc

    token = create_access_token(
        participant_id=participant.id,
        public_id=participant.public_id,
        auth_version=participant.auth_version,
    )
    return TokenResponse(
        access_token=token,
        public_id=participant.public_id,
        must_change_pin=participant.must_change_pin,
    )


def complete_pin_change(db: Session, participant: Participant, payload: ChangePinRequest) -> TokenResponse:
    try:
        change_participant_pin(
            db,
            participant=participant,
            new_pin=payload.pin,
            pin_confirmation=payload.pin_confirmation,
        )
    except AccountError as exc:
        raise AuthError(
            exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            extra=exc.extra,
        ) from exc

    db.refresh(participant)
    token = create_access_token(
        participant_id=participant.id,
        public_id=participant.public_id,
        auth_version=participant.auth_version,
    )
    return TokenResponse(
        access_token=token,
        public_id=participant.public_id,
        must_change_pin=False,
    )


def _unique_public_id(db: Session, attempts: int = 5) -> str:
    for _ in range(attempts):
        candidate = generate_public_id()
        exists = db.execute(
            select(Participant.id).where(Participant.public_id == candidate)
        ).first()
        if exists is None:
            return candidate
    raise AuthError("Could not generate a unique participant ID", status_code=500)
