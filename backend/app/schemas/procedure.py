"""Study procedure and data quality API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StudyProcedureResponse(BaseModel):
    version: str
    active: bool
    protocol_version: str | None = None
    required_modules: list[str]
    required_survey_questions: list[str]
    min_session_duration_seconds: int
    max_session_duration_seconds: int
    max_sessions_per_day: int
    min_minutes_between_sessions: int
    study_start_date: str
    study_end_date: str
    participant_target: int
    min_sessions_per_participant: int
    effective_at: str


class ParticipantStudyProgressResponse(BaseModel):
    procedure_version: str
    completed_sessions: int
    required_sessions: int
    next_eligible_session_at: str | None = None
    study_status: str
    today_session_complete: bool
    session_can_start: bool
    session_block_reason: str | None = None
    session_block_message: str | None = None
    study_start_date: str
    study_end_date: str


class DataQualityFlagRecord(BaseModel):
    id: str
    session_id: str
    module_key: str | None = None
    flag_type: str
    severity: str
    reason: str
    review_status: str
    reviewed_by_researcher_id: str | None = None
    reviewed_at: str | None = None
    created_at: str


class FlaggedSessionRecord(BaseModel):
    session_id: str
    public_id: str | None = None
    session_date: str | None = None
    session_status: str | None = None
    flags: list[DataQualityFlagRecord]


class DataQualityDashboardResponse(BaseModel):
    completed_sessions: int
    incomplete_sessions: int
    abandoned_sessions: int
    in_progress_sessions: int
    flagged_sessions: int
    flags_by_type: dict[str, int]
    participants_below_minimum_sessions: list[dict]
    participants_with_repeated_suspicious_results: list[dict]
    total_flags: int
    unresolved_critical_flags: int


class ReviewDataQualityFlagRequest(BaseModel):
    review_status: str = Field(pattern="^(unresolved|reviewed_valid|reviewed_exclude)$")
