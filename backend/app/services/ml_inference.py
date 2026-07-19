"""ML inference and prediction persistence (Phase 2E)."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import joblib
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import DailySession
from app.models.ml_dataset import MLDataset
from app.models.ml_model import MLModel
from app.models.ml_prediction import MLPrediction
from app.models.participant import Participant
from app.services.ml_training import MODELS_DIR, _predict_scores, _row_to_vector
from app.services.research_etl import build_participant_day_record
from app.services.study_guard import (
    StudyGuardError,
    apply_dataset_filter,
    apply_participant_filter,
    assert_model_visible,
    assert_participant_visible,
    is_synthetic_public_id,
)

RISK_LOW_MAX = 0.35
RISK_HIGH_MIN = 0.70


class InferenceError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def risk_level(probability: float) -> str:
    if probability < RISK_LOW_MAX:
        return "low"
    if probability > RISK_HIGH_MIN:
        return "high"
    return "medium"


def prediction_confidence(probability: float, prediction: bool) -> float:
    return round(probability if prediction else 1.0 - probability, 6)


def _artifact_root() -> Path:
    return MODELS_DIR.parent


def _load_model_metadata(model: MLModel) -> dict[str, Any]:
    artifact_file = _artifact_root() / model.artifact_path
    metadata_file = artifact_file.parent / "metadata.json"
    if not metadata_file.exists():
        raise InferenceError(f"Model metadata not found for {model.id}", status_code=500)
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def _load_model_engine(model: MLModel, metadata: dict[str, Any]) -> tuple[Any, str]:
    artifact_file = _artifact_root() / model.artifact_path
    if not artifact_file.exists():
        raise InferenceError(f"Model artifact not found for {model.id}", status_code=500)

    engine = metadata.get("training_engine") or model.metrics.get("training_engine", "lightgbm")
    if artifact_file.suffix == ".joblib":
        engine = "sklearn_hist_gradient_boosting"
        return joblib.load(artifact_file), engine

    try:
        import lightgbm as lgb
    except (OSError, FileNotFoundError, ImportError) as exc:
        raise InferenceError(
            "LightGBM native library failed to load for inference",
            status_code=500,
        ) from exc

    booster = lgb.Booster(model_file=str(artifact_file))
    return booster, "lightgbm"


def _resolve_participant(db: Session, participant_id: UUID) -> Participant:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise InferenceError("Participant not found", status_code=404)
    return participant


def _get_session(db: Session, participant_id: UUID, session_date: date) -> DailySession:
    session = db.execute(
        select(DailySession)
        .options(selectinload(DailySession.module_results))
        .where(
            DailySession.participant_id == participant_id,
            DailySession.session_date == session_date,
        )
    ).scalar_one_or_none()
    if session is None:
        raise InferenceError("Session not found for participant and date", status_code=404)
    return session


def extract_session_features(
    *,
    participant: Participant,
    session: DailySession,
) -> tuple[dict[str, Any], dict[str, bool]]:
    game_payload = participant.game_data.game_data if participant.game_data else None
    return build_participant_day_record(
        participant=participant,
        session=session,
        game_data=game_payload,
    )


def _features_used_payload(features: dict[str, Any], feature_names: list[str]) -> dict[str, Any]:
    return {name: features.get(name) for name in feature_names}


def _run_inference(
    model_engine: Any,
    engine: str,
    features: dict[str, Any],
    feature_names: list[str],
) -> tuple[float, bool, float]:
    vector = np.array([_row_to_vector(features, feature_names)], dtype=float)
    probability = float(_predict_scores(model_engine, vector, engine)[0])
    probability = max(0.0, min(1.0, probability))
    predicted = probability >= 0.5
    confidence = prediction_confidence(probability, predicted)
    return round(probability, 6), predicted, confidence


def _upsert_prediction(
    db: Session,
    *,
    model: MLModel,
    participant_id: UUID,
    session_date: date,
    probability: float,
    prediction: bool,
    confidence: float,
    features_used: dict[str, Any],
) -> MLPrediction:
    existing = db.execute(
        select(MLPrediction).where(
            MLPrediction.model_id == model.id,
            MLPrediction.participant_id == participant_id,
            MLPrediction.session_date == session_date,
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.probability = probability
        existing.prediction = prediction
        existing.confidence = confidence
        existing.features_used = features_used
        existing.created_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    record = MLPrediction(
        id=uuid.uuid4(),
        model_id=model.id,
        participant_id=participant_id,
        session_date=session_date,
        probability=probability,
        prediction=prediction,
        confidence=confidence,
        features_used=features_used,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def predict_participant_session(
    db: Session,
    *,
    model_id: UUID,
    participant_id: UUID,
    session_date: date,
) -> MLPrediction:
    model = db.get(MLModel, model_id)
    if model is None:
        raise InferenceError("Model not found", status_code=404)
    try:
        assert_model_visible(db, model)
    except StudyGuardError as exc:
        raise InferenceError(exc.message, status_code=exc.status_code) from exc

    participant = db.execute(
        select(Participant)
        .options(selectinload(Participant.game_data))
        .where(Participant.id == participant_id)
    ).scalar_one_or_none()
    if participant is None:
        raise InferenceError("Participant not found", status_code=404)
    try:
        assert_participant_visible(participant)
    except StudyGuardError as exc:
        raise InferenceError(exc.message, status_code=exc.status_code) from exc

    session = _get_session(db, participant.id, session_date)
    features, quality_flags = extract_session_features(participant=participant, session=session)
    if not quality_flags.get("valid_for_ml"):
        raise InferenceError(
            "Session is not eligible for prediction (requires complete core modules)",
            status_code=422,
        )

    metadata = _load_model_metadata(model)
    feature_names = metadata.get("feature_names") or []
    if not feature_names:
        raise InferenceError("Model feature metadata is missing", status_code=500)

    model_engine, engine = _load_model_engine(model, metadata)
    probability, predicted, confidence = _run_inference(model_engine, engine, features, feature_names)

    return _upsert_prediction(
        db,
        model=model,
        participant_id=participant.id,
        session_date=session_date,
        probability=probability,
        prediction=predicted,
        confidence=confidence,
        features_used=_features_used_payload(features, feature_names),
    )


def batch_predict(db: Session, *, model_id: UUID) -> dict[str, int]:
    model = db.get(MLModel, model_id)
    if model is None:
        raise InferenceError("Model not found", status_code=404)
    try:
        assert_model_visible(db, model)
    except StudyGuardError as exc:
        raise InferenceError(exc.message, status_code=exc.status_code) from exc

    metadata = _load_model_metadata(model)
    feature_names = metadata.get("feature_names") or []
    if not feature_names:
        raise InferenceError("Model feature metadata is missing", status_code=500)

    model_engine, engine = _load_model_engine(model, metadata)

    participants = db.execute(
        apply_participant_filter(
            select(Participant)
            .options(
                selectinload(Participant.game_data),
                selectinload(Participant.daily_sessions).selectinload(DailySession.module_results),
            )
        )
    ).scalars().all()

    processed_rows = 0
    successful_predictions = 0
    failed_predictions = 0

    for participant in participants:
        if is_synthetic_public_id(participant.public_id):
            continue
        for session in participant.daily_sessions:
            processed_rows += 1
            try:
                features, quality_flags = build_participant_day_record(
                    participant=participant,
                    session=session,
                    game_data=participant.game_data.game_data if participant.game_data else None,
                )
                if not quality_flags.get("valid_for_ml"):
                    failed_predictions += 1
                    continue

                probability, predicted, confidence = _run_inference(
                    model_engine,
                    engine,
                    features,
                    feature_names,
                )
                _upsert_prediction(
                    db,
                    model=model,
                    participant_id=participant.id,
                    session_date=session.session_date,
                    probability=probability,
                    prediction=predicted,
                    confidence=confidence,
                    features_used=_features_used_payload(features, feature_names),
                )
                successful_predictions += 1
            except Exception:
                failed_predictions += 1

    return {
        "processed_rows": processed_rows,
        "successful_predictions": successful_predictions,
        "failed_predictions": failed_predictions,
    }


def list_predictions(db: Session) -> list[dict[str, Any]]:
    query = (
        select(MLPrediction, Participant, MLModel)
        .join(Participant, MLPrediction.participant_id == Participant.id)
        .join(MLModel, MLPrediction.model_id == MLModel.id)
        .join(MLDataset, MLModel.dataset_id == MLDataset.id)
        .order_by(MLPrediction.created_at.desc())
    )
    query = apply_participant_filter(query)
    query = apply_dataset_filter(query)
    rows = db.execute(query).all()

    return [_serialize_prediction(prediction, participant, model) for prediction, participant, model in rows]


def get_participant_predictions(db: Session, participant_id: UUID) -> list[dict[str, Any]]:
    participant = _resolve_participant(db, participant_id)
    try:
        assert_participant_visible(participant)
    except StudyGuardError as exc:
        raise InferenceError(exc.message, status_code=exc.status_code) from exc
    rows = db.execute(
        apply_dataset_filter(
            select(MLPrediction, MLModel)
            .join(MLModel, MLPrediction.model_id == MLModel.id)
            .join(MLDataset, MLModel.dataset_id == MLDataset.id)
            .where(MLPrediction.participant_id == participant.id)
            .order_by(MLPrediction.session_date.desc(), MLPrediction.created_at.desc())
        )
    ).all()

    return [
        _serialize_prediction(prediction, participant, model)
        for prediction, model in rows
    ]


def _serialize_prediction(
    prediction: MLPrediction,
    participant: Participant,
    model: MLModel,
) -> dict[str, Any]:
    return {
        "id": prediction.id,
        "model_id": prediction.model_id,
        "participant_id": prediction.participant_id,
        "public_id": participant.public_id,
        "session_date": prediction.session_date,
        "probability": prediction.probability,
        "prediction": prediction.prediction,
        "confidence": prediction.confidence,
        "risk_level": risk_level(prediction.probability),
        "model_version": model.model_version,
        "created_at": prediction.created_at,
    }


def prediction_summary(db: Session) -> dict[str, Any]:
    predictions = db.execute(select(MLPrediction)).scalars().all()
    if not predictions:
        return {
            "total_predictions": 0,
            "high_risk_count": 0,
            "average_probability": 0.0,
        }

    high_risk_count = sum(1 for item in predictions if risk_level(item.probability) == "high")
    average_probability = round(
        sum(item.probability for item in predictions) / len(predictions),
        6,
    )
    return {
        "total_predictions": len(predictions),
        "high_risk_count": high_risk_count,
        "average_probability": average_probability,
    }
