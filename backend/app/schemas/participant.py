from datetime import datetime

from pydantic import BaseModel

from app.models.participant import Participant
from app.services.participant_account_service import account_state_payload, resolve_display_status


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
        )
