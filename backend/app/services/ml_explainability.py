"""SHAP explainability for trained ML models (Phase 2F)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml_explanation import MLExplanation
from app.models.ml_dataset import MLDataset
from app.models.ml_model import MLModel
from app.models.ml_prediction import MLPrediction
from app.models.participant import Participant
from app.services.ml_inference import _load_model_engine, _load_model_metadata
from app.services.ml_training import _row_to_vector
from app.services.study_guard import (
    StudyGuardError,
    apply_dataset_filter,
    apply_participant_filter,
    assert_model_visible,
    assert_participant_visible,
)

TOP_CONTRIBUTION_COUNT = 10
TOP_RISK_FACTOR_COUNT = 3


class ExplainabilityError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _sigmoid(value: float) -> float:
    return float(1.0 / (1.0 + np.exp(-value)))


def _direction(impact: float) -> str:
    return "increases_risk" if impact >= 0 else "decreases_risk"


def _build_contributions(
    feature_names: list[str],
    feature_values: dict[str, Any],
    shap_values: np.ndarray,
) -> list[dict[str, Any]]:
    contributions: list[dict[str, Any]] = []
    for index, feature in enumerate(feature_names):
        impact = float(shap_values[index])
        contributions.append(
            {
                "feature": feature,
                "value": feature_values.get(feature),
                "impact": round(impact, 6),
                "direction": _direction(impact),
            }
        )
    contributions.sort(key=lambda item: abs(item["impact"]), reverse=True)
    return contributions[:TOP_CONTRIBUTION_COUNT]


def _compute_shap_values(
    model_engine: Any,
    engine: str,
    feature_vector: np.ndarray,
    feature_names: list[str],
) -> tuple[np.ndarray, float]:
    try:
        import shap
    except ImportError as exc:
        raise ExplainabilityError("SHAP is not installed", status_code=500) from exc

    if engine == "lightgbm":
        explainer = shap.TreeExplainer(model_engine)
        shap_result = explainer.shap_values(feature_vector)
        expected = explainer.expected_value
        if isinstance(shap_result, list):
            values = np.array(shap_result[1 if len(shap_result) > 1 else 0])[0]
            if isinstance(expected, (list, np.ndarray)):
                base = float(expected[1 if len(expected) > 1 else 0])
            else:
                base = float(expected)
        else:
            values = np.array(shap_result)[0]
            base = float(expected)
        return values, _sigmoid(base)

    explainer = shap.Explainer(model_engine, feature_vector)
    explanation = explainer(feature_vector)
    values = np.array(explanation.values)[0]
    base_raw = explanation.base_values
    base = float(np.array(base_raw).reshape(-1)[0])
    if base > 1.0 or base < 0.0:
        base = _sigmoid(base)
    return values, base


def build_explanation_payload(
    *,
    prediction: MLPrediction,
    model: MLModel,
    feature_names: list[str],
) -> dict[str, Any]:
    metadata = _load_model_metadata(model)
    model_engine, engine = _load_model_engine(model, metadata)
    feature_vector = np.array(
        [_row_to_vector(prediction.features_used, feature_names)],
        dtype=float,
    )
    shap_values, base_value = _compute_shap_values(model_engine, engine, feature_vector, feature_names)
    contributions = _build_contributions(feature_names, prediction.features_used, shap_values)
    top_risk_factors = [
        item["feature"]
        for item in contributions
        if item["direction"] == "increases_risk"
    ][:TOP_RISK_FACTOR_COUNT]

    return {
        "prediction_probability": round(prediction.probability, 6),
        "base_value": round(base_value, 6),
        "contributions": contributions,
        "top_risk_factors": top_risk_factors,
    }


def generate_explanation(db: Session, *, prediction_id: UUID) -> MLExplanation:
    prediction = db.get(MLPrediction, prediction_id)
    if prediction is None:
        raise ExplainabilityError("Prediction not found", status_code=404)

    model = db.get(MLModel, prediction.model_id)
    if model is None:
        raise ExplainabilityError("Model not found", status_code=404)

    participant = db.get(Participant, prediction.participant_id)
    if participant is None:
        raise ExplainabilityError("Participant not found", status_code=404)
    try:
        assert_model_visible(db, model)
        assert_participant_visible(participant)
    except StudyGuardError as exc:
        raise ExplainabilityError(exc.message, status_code=exc.status_code) from exc

    metadata = _load_model_metadata(model)
    feature_names = metadata.get("feature_names") or []
    if not feature_names:
        raise ExplainabilityError("Model feature metadata is missing", status_code=500)

    payload = build_explanation_payload(
        prediction=prediction,
        model=model,
        feature_names=feature_names,
    )

    existing = db.execute(
        select(MLExplanation).where(MLExplanation.prediction_id == prediction_id)
    ).scalar_one_or_none()

    if existing is not None:
        existing.explanation = payload
        existing.created_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing

    record = MLExplanation(
        id=uuid.uuid4(),
        prediction_id=prediction.id,
        model_id=prediction.model_id,
        participant_id=prediction.participant_id,
        explanation=payload,
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_explanation(db: Session, *, prediction_id: UUID) -> MLExplanation:
    record = db.execute(
        select(MLExplanation).where(MLExplanation.prediction_id == prediction_id)
    ).scalar_one_or_none()
    if record is None:
        raise ExplainabilityError(
            "Explanation not found. Run POST /predictions/{id}/explain first",
            status_code=404,
        )

    prediction = db.get(MLPrediction, prediction_id)
    if prediction is None:
        raise ExplainabilityError("Prediction not found", status_code=404)
    model = db.get(MLModel, prediction.model_id)
    participant = db.get(Participant, prediction.participant_id)
    if model is None or participant is None:
        raise ExplainabilityError("Explanation not found", status_code=404)
    try:
        assert_model_visible(db, model)
        assert_participant_visible(participant)
    except StudyGuardError as exc:
        raise ExplainabilityError(exc.message, status_code=exc.status_code) from exc
    return record


def get_model_feature_importance(db: Session, *, model_id: UUID) -> dict[str, Any]:
    model = db.get(MLModel, model_id)
    if model is None:
        raise ExplainabilityError("Model not found", status_code=404)
    try:
        assert_model_visible(db, model)
    except StudyGuardError as exc:
        raise ExplainabilityError(exc.message, status_code=exc.status_code) from exc

    training_items = model.feature_importance.get("features") or []
    training_ranked = [
        {"feature": item["feature"], "importance": item["importance"]}
        for item in training_items
    ]

    explanations = db.execute(
        apply_participant_filter(
            select(MLExplanation)
            .join(Participant, MLExplanation.participant_id == Participant.id)
            .where(MLExplanation.model_id == model_id)
        )
    ).scalars().all()

    shap_totals: dict[str, list[float]] = {}
    for record in explanations:
        for item in record.explanation.get("contributions") or []:
            feature = item.get("feature")
            impact = item.get("impact")
            if feature and impact is not None:
                shap_totals.setdefault(feature, []).append(abs(float(impact)))

    shap_average = [
        {
            "feature": feature,
            "importance": round(sum(values) / len(values), 6),
        }
        for feature, values in shap_totals.items()
    ]
    shap_average.sort(key=lambda item: item["importance"], reverse=True)

    ranked_map: dict[str, float] = {}
    for item in training_ranked:
        ranked_map[item["feature"]] = ranked_map.get(item["feature"], 0.0) + item["importance"]
    for item in shap_average:
        ranked_map[item["feature"]] = ranked_map.get(item["feature"], 0.0) + item["importance"]

    ranked_features = [
        {"feature": feature, "score": round(score, 6)}
        for feature, score in sorted(ranked_map.items(), key=lambda pair: pair[1], reverse=True)
    ]

    return {
        "model_id": model.id,
        "model_version": model.model_version,
        "training_feature_importance": training_ranked,
        "shap_average_importance": shap_average,
        "ranked_features": ranked_features[:TOP_CONTRIBUTION_COUNT],
    }


def compare_models(db: Session) -> list[dict[str, Any]]:
    query = (
        select(MLModel)
        .join(MLDataset, MLModel.dataset_id == MLDataset.id)
        .order_by(MLModel.created_at.desc())
    )
    query = apply_dataset_filter(query)
    models = db.execute(query).scalars().all()
    comparisons: list[dict[str, Any]] = []
    for model in models:
        split_metrics = (
            model.metrics.get("test")
            or model.metrics.get("validation")
            or model.metrics.get("train")
            or {}
        )
        comparisons.append(
            {
                "model_id": model.id,
                "version": model.model_version,
                "accuracy": split_metrics.get("accuracy"),
                "f1": split_metrics.get("f1_score"),
                "roc_auc": split_metrics.get("roc_auc"),
                "training_rows": model.metrics.get("train_rows", model.train_size),
                "created_at": model.created_at,
            }
        )
    return comparisons
