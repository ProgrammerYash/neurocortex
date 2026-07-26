from pydantic import BaseModel, Field


class BulkSelectionRequest(BaseModel):
    participant_public_ids: list[str] | None = None
    selection_mode: str | None = None
    filters: dict | None = None
    excluded_public_ids: list[str] | None = None


class BulkMessageRequest(BulkSelectionRequest):
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=8000)


class BulkEmailRequest(BulkMessageRequest):
    pass


class BulkSuspendRequest(BulkSelectionRequest):
    duration: str = Field(..., min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=500)


class BulkReactivateRequest(BulkSelectionRequest):
    reason: str | None = Field(default=None, max_length=500)


class BulkRemoveRequest(BulkSelectionRequest):
    reason: str = Field(..., min_length=1, max_length=500)


class BulkActionResult(BaseModel):
    requested_count: int
    eligible_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    failures: list[dict] = Field(default_factory=list)
