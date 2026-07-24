from datetime import datetime

from pydantic import BaseModel


class ParticipantModelFeedbackResponse(BaseModel):
    status: str
    label: str | None = None
    category: str | None = None
    generated_at: datetime | str | None = None
    model_version: str | None = None
