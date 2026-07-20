from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ParticipantConsentSubmitRequest(BaseModel):
    participant_printed_name: str = Field(..., min_length=2, max_length=200)
    guardian_printed_name: str = Field(..., min_length=2, max_length=200)
    participant_acknowledged: bool
    guardian_acknowledged: bool
    participant_signature_png: str = Field(..., min_length=32, max_length=1_400_100)
    guardian_signature_png: str = Field(..., min_length=32, max_length=1_400_100)
    consent_version: str = Field(..., min_length=1, max_length=64)
    survey_version: str = Field(..., min_length=1, max_length=64)
    template_sha256: str = Field(..., pattern="^[0-9a-f]{64}$")
    idempotency_key: UUID

    @field_validator("participant_printed_name", "guardian_printed_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


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
    consent_required: bool
    consent_recorded: bool


class CurrentConsentResponse(BaseModel):
    consent_version: str
    survey_version: str
    template_sha256: str
    student_researcher: str
    project_title: str
    purpose: str
    participation_activities: str
    time_required: str
    potential_risks: str
    potential_benefits: str
    confidentiality: str
    questions_contact: str
    adult_sponsor: str
    adult_sponsor_contact: str
    voluntary_participation: str
    may_stop: str
    may_skip_questions: str
    signing_explanation: str
    participant_acknowledgment: str
    guardian_acknowledgment: str


class ResearcherConsentItem(BaseModel):
    id: UUID
    participant_id: str
    participant_printed_name: str
    guardian_printed_name: str
    participant_signed_at: datetime
    guardian_signed_at: datetime
    consent_version: str
    survey_version: str
    status: str


class ResearcherConsentPage(BaseModel):
    items: list[ResearcherConsentItem]
    total: int
    limit: int
    offset: int
