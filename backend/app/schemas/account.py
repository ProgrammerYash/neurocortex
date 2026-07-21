from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class AccountReasonRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("reason must be at least 3 characters")
        return cleaned


class SuspendParticipantRequest(AccountReasonRequest):
    duration: str = Field(..., pattern="^(24_hours|48_hours|1_week|1_month|indefinite)$")


class RemoveAccountRequest(AccountReasonRequest):
    confirmation_public_id: str = Field(..., min_length=4, max_length=32)

    @field_validator("confirmation_public_id")
    @classmethod
    def normalize_public_id(cls, value: str) -> str:
        return value.strip().upper()


class AccountActionResponse(BaseModel):
    actionType: str
    participantId: str
    authVersion: int
    isSuspended: bool
    suspendedAt: datetime | None = None
    suspendedUntil: datetime | None = None
    suspensionReason: str | None = None
    suspendedUntilDisplay: str | None = None
    isDisabled: bool
    disabledAt: datetime | None = None
    disabledReason: str | None = None
    isRemoved: bool
    removedAt: datetime | None = None
    removalReason: str | None = None
    mustChangePin: bool
    temporaryPin: str | None = None


class AccountActionRecord(BaseModel):
    id: str
    actionType: str
    reason: str
    durationCode: str | None = None
    researcherDisplayName: str | None = None
    createdAt: datetime
    createdAtDisplay: str | None = None


class AccountActionListResponse(BaseModel):
    items: list[AccountActionRecord]
