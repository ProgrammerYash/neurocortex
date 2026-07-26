from pydantic import BaseModel, ConfigDict, Field


class GroqProviderStatusResponse(BaseModel):
    configured: bool
    provider: str
    status: str
    model: str | None = None


class ParticipantModelFeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str
    label: str | None = None
    level: str | None = None
    headline: str | None = None
    summary: str | None = None
    factors: list[str] | None = None
    generated_at: str | None = None
    source_session_count: int | None = None
    warning: str | None = None
