from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SignerRecord(BaseModel):
    role: str
    printed_name: str | None = None
    degree_or_license: str | None = None
    approval_date: str | None = None
    signature_status: str | None = None


class Form4DraftRequest(BaseModel):
    project_title: str | None = None
    student_researcher_names: str | None = None
    adult_sponsor: str | None = None
    adult_sponsor_contact: str | None = None


class Form4UpdateRequest(BaseModel):
    student_researcher_names: str | None = None
    project_title: str | None = None
    adult_sponsor: str | None = None
    adult_sponsor_contact: str | None = None
    research_plan_submitted: bool | None = None
    surveys_attached: bool | None = None
    published_instruments_legally_obtained: bool | None = None
    informed_consent_attached: bool | None = None
    qualified_scientist: bool | None = None
    full_committee_review: bool | None = None
    risk_level: str | None = Field(default=None, pattern="^(minimal|more_than_minimal)$")
    qualified_scientist_required: bool | None = None
    risk_assessment_required: bool | None = None
    minor_assent_required: str | None = Field(default=None, pattern="^(yes|no|not_applicable)$")
    parental_permission_required: str | None = Field(default=None, pattern="^(yes|no|not_applicable)$")
    adult_informed_consent_required: str | None = Field(default=None, pattern="^(yes|no|not_applicable)$")
    signer_records: list[SignerRecord] | None = None


class DocumentStatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(awaiting_irb|approved|void|superseded)$")
    confirm_approved: bool = False


class DocumentSummary(BaseModel):
    id: UUID
    document_type: str
    protocol_version: str
    template_version: str
    template_id: str | None = None
    status: str
    project_title: str | None = None
    completion_percentage: float
    generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    has_generated_pdf: bool = False


class DocumentDetail(BaseModel):
    id: UUID
    document_type: str
    protocol_id: UUID
    protocol_version: str
    template_version: str
    template_id: str | None = None
    status: str
    artifact_hash: str | None = None
    generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    form4: Form4UpdateRequest | None = None
    completion_percentage: float
    has_generated_pdf: bool = False


class GenerateDocumentResponse(BaseModel):
    document_id: UUID
    status: str
    artifact_hash: str
    generated_at: datetime
