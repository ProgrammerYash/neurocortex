from pydantic import BaseModel, Field


class ParticipantConsentSubmitRequest(BaseModel):
    assent_acknowledged: bool | None = None
    parental_permission_status: str | None = Field(default=None, pattern="^(declined|pending)$")
    adult_consent_acknowledged: bool | None = None


class ResearcherConsentEventRequest(BaseModel):
    event_type: str
    status: str | None = None
    form_type: str | None = None
    acknowledged_at: str | None = None
    metadata: dict | None = None


class ResolveAgeConsentCategoryRequest(BaseModel):
    age_consent_category: str = Field(..., pattern="^(under_18|age_18_or_over)$")


class ConsentStatusResponse(BaseModel):
    participant_id: str
    age_range: str
    age_consent_category: str
    protocol_version: str
    age_category: str
    required_consent_types: list[str]
    assent_status: str
    parental_permission_status: str
    adult_consent_status: str
    withdrawal_status: str
    deletion_requested: bool
    excluded_from_ml: bool
    session_eligible: bool
    session_block_reason: str | None = None
    session_block_message: str | None = None
    ml_eligible: bool
    ml_block_reason: str | None = None
    require_consent_for_sessions: bool
