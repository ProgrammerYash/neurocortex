from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PredictRequest(BaseModel):
    participant_id: UUID
    session_date: date


class PredictResponse(BaseModel):
    prediction_id: UUID
    probability: float
    prediction: bool
    risk_level: str
    confidence: float


class BatchPredictResponse(BaseModel):
    processed_rows: int
    successful_predictions: int
    failed_predictions: int


class PredictionRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: UUID
    participant_id: UUID
    public_id: str
    session_date: date
    probability: float
    prediction: bool
    confidence: float
    risk_level: str
    model_version: int
    created_at: datetime


class PredictionSummary(BaseModel):
    total_predictions: int
    high_risk_count: int
    average_probability: float
