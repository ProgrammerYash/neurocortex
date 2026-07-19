from datetime import datetime

from pydantic import BaseModel

from app.models.participant import Participant


class ParticipantMeResponse(BaseModel):
    public_id: str
    grade: str
    age_range: str
    pet_choice: str
    joined_at: datetime

    @classmethod
    def from_participant(cls, participant: Participant) -> "ParticipantMeResponse":
        return cls(
            public_id=participant.public_id,
            grade=participant.grade,
            age_range=participant.age_range,
            pet_choice=participant.pet_choice,
            joined_at=participant.created_at,
        )
