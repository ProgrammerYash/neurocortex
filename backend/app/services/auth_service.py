from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.participant import Participant
from app.schemas.auth import (
    ParticipantLoginRequest,
    ParticipantRegisterRequest,
    ParticipantProfile,
    RegisterResponse,
    TokenResponse,
)
from app.utils.ids import generate_public_id
from app.utils.security import create_access_token, hash_pin, verify_pin


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def register_participant(db: Session, payload: ParticipantRegisterRequest) -> RegisterResponse:
    from app.services.consent_service import record_participant_consent, validate_registration_consent_category

    consent_category = validate_registration_consent_category(payload.age_range, payload.age_consent_category)
    public_id = _unique_public_id(db)
    participant = Participant(
        public_id=public_id,
        pin_hash=hash_pin(payload.pin),
        grade=payload.grade,
        age_range=payload.age_range,
        age_consent_category=consent_category,
        pet_choice=payload.pet_choice,
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)

    consent_payload = {
        key: value
        for key, value in {
            "assent_acknowledged": payload.assent_acknowledged,
            "parental_permission_status": payload.parental_permission_status,
            "adult_consent_acknowledged": payload.adult_consent_acknowledged,
        }.items()
        if value is not None
    }
    if consent_payload:
        from app.services.consent_service import record_participant_consent

        record_participant_consent(db, participant=participant, payload=consent_payload)

    token = create_access_token(participant_id=participant.id, public_id=participant.public_id)
    return RegisterResponse(
        access_token=token,
        public_id=participant.public_id,
        participant=ParticipantProfile.model_validate(participant),
    )


def login_participant(db: Session, payload: ParticipantLoginRequest) -> TokenResponse:
    participant = db.execute(
        select(Participant).where(Participant.public_id == payload.public_id)
    ).scalar_one_or_none()
    if participant is None or not verify_pin(payload.pin, participant.pin_hash):
        raise AuthError("Invalid public ID or PIN", status_code=401)

    token = create_access_token(participant_id=participant.id, public_id=participant.public_id)
    return TokenResponse(
        access_token=token,
        public_id=participant.public_id,
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
