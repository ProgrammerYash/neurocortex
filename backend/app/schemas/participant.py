from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.participant import Participant
from app.services.participant_account_service import resolve_display_status
from app.services.study_frequency import ALLOWED_STUDY_FREQUENCIES, validate_study_frequency


class ParticipantMeResponse(BaseModel):
    public_id: str
    grade: str
    age_range: str
    pet_choice: str
    joined_at: datetime
    consent_required: bool
    consent_recorded: bool
    must_change_pin: bool
    account_status: str
    study_frequency: str | None = None

    @classmethod
    def from_participant(
        cls,
        participant: Participant,
        *,
        consent_recorded: bool,
        withdrawal_status: str | None = None,
        last_active_at: datetime | None = None,
        sessions_started: int = 0,
    ) -> "ParticipantMeResponse":
        status = resolve_display_status(
            participant,
            withdrawal_status=withdrawal_status,
            last_active_at=last_active_at,
            sessions_started=sessions_started,
        )
        return cls(
            public_id=participant.public_id,
            grade=participant.grade,
            age_range=participant.age_range,
            pet_choice=participant.pet_choice,
            joined_at=participant.created_at,
            consent_required=not consent_recorded,
            consent_recorded=consent_recorded,
            must_change_pin=participant.must_change_pin,
            account_status=status,
            study_frequency=participant.study_frequency,
        )


class ParticipantPreferencesUpdateRequest(BaseModel):
    study_frequency: str = Field(..., min_length=1, max_length=32)

    @field_validator("study_frequency")
    @classmethod
    def validate_frequency(cls, value: str) -> str:
        return validate_study_frequency(value)


class ParticipantPreferencesResponse(BaseModel):
    study_frequency: str

    @classmethod
    def from_participant(cls, participant: Participant) -> "ParticipantPreferencesResponse":
        if participant.study_frequency not in ALLOWED_STUDY_FREQUENCIES:
            raise ValueError("Participant has no saved study frequency")
        return cls(study_frequency=participant.study_frequency)
