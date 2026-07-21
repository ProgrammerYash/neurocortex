from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SendMessageRequest(BaseModel):
    subject: str = Field(..., max_length=150)
    body: str = Field(..., max_length=5000)

    @field_validator("subject", "body")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class MessageResponse(BaseModel):
    id: str
    participantId: str | None = None
    subject: str
    body: str | None = None
    createdAt: datetime
    createdAtDisplay: str | None = None
    readAt: datetime | None = None
    readAtDisplay: str | None = None
    isRead: bool
    researcherDisplayName: str | None = None


class MessagePage(BaseModel):
    items: list[MessageResponse]
    total: int
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    unread_count: int
