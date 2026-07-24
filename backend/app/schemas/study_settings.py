from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool


class StudySettingsResponse(BaseModel):
    participant_feedback_enabled: bool
    participant_feedback_updated_at: datetime | None = None
    participant_feedback_updated_by: UUID | None = None
    model_configured: bool
    model_version: str | None = None


class StudySettingsUpdateRequest(BaseModel):
    participant_feedback_enabled: StrictBool
