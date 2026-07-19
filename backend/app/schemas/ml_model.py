from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TrainModelRequest(BaseModel):
    dataset_id: UUID
    target_label: str = Field(default="burnout_next_day", max_length=64)
    model_type: str = Field(default="lightgbm", max_length=32)


class TrainModelResponse(BaseModel):
    model_id: UUID
    status: str
    metrics: dict


class MLModelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    model_type: str
    target_label: str
    feature_schema_version: str
    label_schema_version: str | None
    model_version: int
    train_size: int
    validation_size: int
    test_size: int
    metrics: dict
    created_at: datetime


class MLModelDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    model_type: str
    target_label: str
    feature_schema_version: str
    label_schema_version: str | None
    model_version: int
    train_size: int
    validation_size: int
    test_size: int
    metrics: dict
    feature_importance: dict
    artifact_path: str
    created_at: datetime
