from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BuildDatasetRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    dataset_mode: str = Field(default="strict", pattern="^(strict|exploratory)$")


class DatasetMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    feature_schema_version: str
    label_schema_version: str | None = None
    dataset_version: int
    row_count: int
    participant_count: int
    date_range_start: date | None
    date_range_end: date | None
    labels_generated_at: datetime | None = None
    dataset_mode: str = "strict"
    created_at: datetime


class DatasetRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    participant_id: UUID
    public_id: str
    session_date: date
    session_id: UUID | None = None
    features: dict
    quality_flags: dict
    exclusion_reasons: list[str] | None = None
    labels: dict = Field(default_factory=dict)


class DatasetRowPage(BaseModel):
    items: list[DatasetRow]
    total: int
    limit: int
    offset: int


class DatasetSummary(BaseModel):
    dataset_id: UUID
    name: str
    feature_schema_version: str
    dataset_version: int
    row_count: int
    participant_count: int
    date_range_start: date | None
    date_range_end: date | None
    complete_day_count: int
    valid_for_ml_count: int
    missing_reaction_count: int
    missing_typing_count: int
    missing_memory_count: int
    missing_attention_count: int
    missing_survey_count: int
    missing_tlx_count: int
    missing_game_count: int
    gamification_snapshot_rows: int


class LabelGenerationResponse(BaseModel):
    dataset_id: UUID
    dataset_version: int
    feature_schema_version: str
    label_schema_version: str
    generated_at: datetime
    row_count: int
    labeled_rows: int
    burnout_next_day_labeled: int
    burnout_next_day_true: int
    burnout_next_day_false: int
    burnout_prevalence: float | None
    high_workload_next_day_true: int
    study_dropout_true: int
    valid_training_rows: int


class DatasetStatisticsResponse(BaseModel):
    dataset_id: UUID
    dataset_version: int
    feature_schema_version: str
    label_schema_version: str
    schema_version: str
    artifact_version: int | None = None
    created_at: datetime | None = None
    participant_count: int
    row_count: int
    rows_per_participant: dict
    study_duration_days: int | None
    average_sessions_per_participant: float
    completion_rate: float
    valid_training_row_count: int
    missing_values_per_feature: dict
    feature_statistics: dict


class CorrelationPair(BaseModel):
    feature_a: str
    feature_b: str
    pearson: float | None
    spearman: float | None
    sample_count: int


class DatasetCorrelationsResponse(BaseModel):
    dataset_id: UUID
    dataset_version: int
    feature_schema_version: str
    label_schema_version: str
    schema_version: str
    artifact_version: int | None = None
    created_at: datetime | None = None
    feature_count: int
    pair_count: int
    pairs: list[CorrelationPair]


class DatasetQualityResponse(BaseModel):
    dataset_id: UUID
    dataset_version: int
    feature_schema_version: str
    label_schema_version: str
    schema_version: str
    artifact_version: int | None = None
    created_at: datetime | None = None
    row_count: int
    participant_count: int
    missing_percentages: dict
    average_missing_percent: float
    duplicate_rows: int
    duplicate_row_rate: float
    participant_imbalance: dict
    sessions_per_participant: dict
    valid_training_rows: int
    valid_training_row_rate: float
    burnout_prevalence_percent: float | None
    dropout_prevalence_percent: float
    average_completion_rate: float
    quality_score: float


class DatasetLabelsResponse(BaseModel):
    dataset_id: UUID
    dataset_version: int
    feature_schema_version: str
    label_schema_version: str
    generated_at: datetime | None = None
    artifact_version: int | None = None
    row_count: int
    labeled_rows: int
    burnout_next_day_labeled: int
    burnout_next_day_true: int
    burnout_next_day_false: int
    burnout_prevalence: float | None
    high_workload_next_day_true: int
    study_dropout_true: int
    valid_training_rows: int
