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
    autoDataConfigured: bool = False
    autoDataStartDate: str | None = None
    autoDataEndDate: str | None = None
    autoDataFrequency: str | None = None
    autoDataWeekdays: list[int] | None = None
    autoDataPaused: bool = False


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
    amount: int = Field(ge=1)


class GoldenVaultAutoDataRequest(BaseModel):
    start_date: str
    end_date: str | None = None
    frequency: str | None = None
    weekdays: list[int] | None = None
    enable_future: bool = True


class GoldenVaultAutoDataPatchRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    frequency: str | None = None
    weekdays: list[int] | None = None
    paused: bool | None = None


class GoldenVaultAutoDataPreviewResponse(BaseModel):
    startDate: str
    endDate: str | None = None
    endLabel: str
    frequency: str
    weekdays: list[int]
    scheduledThroughToday: int
    alreadyGenerated: int
    newSessionsToAdd: int
    resultingDisplayedSessions: int
    nextAutoSessionAt: str | None = None


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


class GoldenVaultFakeUsersPreviewRequest(BaseModel):
    total: int = Field(ge=1)
    start_date: str
    daily: int = Field(ge=0, default=0)
    weekly: int = Field(ge=0, default=0)
    two_days: int = Field(ge=0, default=0)
    four_days: int = Field(ge=0, default=0)


class GoldenVaultFakeUsersPreviewResponse(BaseModel):
    totalUsers: int
    startDate: str
    dailyCount: int
    weeklyCount: int
    twoDaysCount: int
    fourDaysCount: int
    estimatedAutoDataEvents: int
    estimatedPdfCount: int
    estimatedGenerationBatches: int


class GoldenVaultFakeUsersGenerateRequest(GoldenVaultFakeUsersPreviewRequest):
    idempotency_key: str | None = Field(default=None, max_length=128)


class GoldenVaultFakeUsersBatchResponse(BaseModel):
    batchId: str
    status: str
    requestedCount: int
    processedCount: int
    successfulCount: int
    failedCount: int
    startDate: str
    dailyCount: int
    weeklyCount: int
    twoDaysCount: int
    fourDaysCount: int
    credentialsAvailable: bool = False
    credentialsViewedAt: str | None = None
    errors: list[str] | None = None


class GoldenVaultFakeUsersProcessResponse(BaseModel):
    batchId: str
    status: str
    processedCount: int
    successfulCount: int
    failedCount: int
    credentialsAvailable: bool = False
    errors: list[str] | None = None


class GoldenVaultFakeUsersCredentialsResponse(BaseModel):
    batchId: str
    credentials: list[dict[str, str]]
