from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GoldenVaultLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=256)


class GoldenVaultLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class GoldenVaultParticipantRow(BaseModel):
    participantId: str
    displayName: str | None = None
    enabled: bool
    realCompletedSessions: int
    bonusSessions: int
    displayedCompletedSessions: int
    earnedCoins: int
    bonusCoins: int
    displayedCoins: int
    feedbackLevel: str | None = None
    feedbackStatus: str | None = None
    updatedAt: str | None = None
    autoSessionEnabled: bool = False
    nextAutoSessionAt: str | None = None
    nextAutoSessionDisplay: str | None = None
    lastAutoSessionAt: str | None = None
    lastAutoSessionDisplay: str | None = None


class GoldenVaultAutoSessionPatchRequest(BaseModel):
    enabled: bool


class GoldenVaultAutoSessionResponse(BaseModel):
    publicId: str
    autoSessionEnabled: bool
    nextAutoSessionAt: str | None = None
    lastAutoSessionAt: str | None = None
    bonusSessions: int
    displayedCompletedSessions: int


class GoldenVaultParticipantListResponse(BaseModel):
    items: list[GoldenVaultParticipantRow]
    total: int
    limit: int
    offset: int


class GoldenVaultPatchRequest(BaseModel):
    enabled: bool | None = None
    bonus_sessions: int | None = Field(default=None, ge=0)
    bonus_coins: int | None = Field(default=None, ge=0)


class GoldenVaultAmountRequest(BaseModel):
    amount: int = Field(ge=0)


class GoldenVaultSessionAdjustRequest(BaseModel):
    delta: int | None = None
    set_to: int | None = Field(default=None, ge=0)


class GoldenVaultCoinAdjustRequest(BaseModel):
    delta: int | None = None
    set_to: int | None = Field(default=None, ge=0)


class GoldenVaultBulkRequest(BaseModel):
    action: str
    participant_public_ids: list[str] | None = None
    selection_mode: Literal["explicit", "all_matching"] | None = "explicit"
    filters: dict[str, Any] | None = None
    excluded_public_ids: list[str] | None = None
    amount: int | None = Field(default=None, ge=0)
    set_to: int | None = Field(default=None, ge=0)


class GoldenVaultBulkResult(BaseModel):
    requested_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    failures: list[dict[str, str]] = Field(default_factory=list)


class GoldenVaultAuditItem(BaseModel):
    event_type: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
