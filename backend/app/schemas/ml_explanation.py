from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExplainResponse(BaseModel):
    prediction_id: UUID
    explanation: dict


class ExplanationDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prediction_id: UUID
    model_id: UUID
    participant_id: UUID
    explanation: dict
    created_at: datetime


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class RankedFeatureItem(BaseModel):
    feature: str
    score: float


class ModelFeatureImportanceResponse(BaseModel):
    model_id: UUID
    model_version: int
    training_feature_importance: list[FeatureImportanceItem]
    shap_average_importance: list[FeatureImportanceItem]
    ranked_features: list[RankedFeatureItem]


class ModelComparisonItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model_id: UUID
    version: int
    accuracy: float | None
    f1: float | None
    roc_auc: float | None
    training_rows: int
    created_at: datetime
