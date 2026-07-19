"""ML model training pipeline (Phase 2D)."""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_row import MLDatasetRow
from app.models.ml_model import MLModel
from app.services.study_guard import (
    StudyGuardError,
    apply_dataset_filter,
    assert_dataset_visible,
    assert_model_visible,
)
from app.services.research_correlations import NON_NUMERIC_FEATURE_KEYS

RANDOM_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
SUPPORTED_MODEL_TYPES = frozenset({"lightgbm"})
SUPPORTED_TARGET_LABELS = frozenset({"burnout_next_day", "high_workload_next_day", "study_dropout"})

LEAKAGE_FEATURE_KEYS = frozenset(
    {
        *NON_NUMERIC_FEATURE_KEYS,
        "days_since_join",
    }
)

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


class TrainingError(Exception):
    def __init__(self, message: str, status_code: int = 422):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def split_participants(participant_ids: list[UUID], seed: int = RANDOM_SEED) -> tuple[set[UUID], set[UUID], set[UUID]]:
    unique_ids = list(dict.fromkeys(participant_ids))
    participant_count = len(unique_ids)
    if participant_count < 3:
        raise TrainingError(
            f"Participant-level split requires at least 3 participants, found {participant_count}",
            status_code=422,
        )

    rng = random.Random(seed)
    shuffled = unique_ids.copy()
    rng.shuffle(shuffled)

    train_count = max(1, int(round(participant_count * TRAIN_RATIO)))
    val_count = max(1, int(round(participant_count * VAL_RATIO)))
    test_count = participant_count - train_count - val_count

    while test_count < 1 and val_count > 1:
        val_count -= 1
        test_count = participant_count - train_count - val_count
    while test_count < 1 and train_count > 1:
        train_count -= 1
        test_count = participant_count - train_count - val_count

    if test_count < 1:
        raise TrainingError("Unable to allocate test participants for split", status_code=422)

    train_ids = set(shuffled[:train_count])
    val_ids = set(shuffled[train_count : train_count + val_count])
    test_ids = set(shuffled[train_count + val_count :])

    overlap = (train_ids & val_ids) | (train_ids & test_ids) | (val_ids & test_ids)
    if overlap:
        raise TrainingError("Participant split produced overlapping assignments", status_code=500)

    return train_ids, val_ids, test_ids


def _extract_feature_names(rows: list[MLDatasetRow]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        for key, value in row.features.items():
            if key in LEAKAGE_FEATURE_KEYS:
                continue
            if _is_number(value):
                keys.add(key)
    return sorted(keys)


def _row_to_vector(features: dict[str, Any], feature_names: list[str]) -> list[float]:
    vector: list[float] = []
    for name in feature_names:
        value = features.get(name)
        if _is_number(value):
            vector.append(float(value))
        else:
            vector.append(float("nan"))
    return vector


def _load_training_rows(db: Session, dataset_id: UUID) -> tuple[MLDataset, list[MLDatasetRow]]:
    dataset = db.get(MLDataset, dataset_id)
    if dataset is None:
        raise TrainingError("Dataset not found", status_code=404)
    try:
        assert_dataset_visible(dataset)
    except StudyGuardError as exc:
        raise TrainingError(exc.message, status_code=exc.status_code) from exc
    if dataset.labels_generated_at is None:
        raise TrainingError(
            "Dataset labels not generated. Run POST /datasets/{id}/label first",
            status_code=422,
        )

    rows = db.execute(
        select(MLDatasetRow).where(MLDatasetRow.dataset_id == dataset_id)
    ).scalars().all()
    rows = [row for row in rows if row.labels.get("valid_training_row") is True]

    if not rows:
        raise TrainingError("No rows with valid_training_row=true found for training", status_code=422)

    return dataset, rows


def _next_model_version(db: Session, dataset_id: UUID) -> int:
    current = db.execute(
        select(func.max(MLModel.model_version)).where(MLModel.dataset_id == dataset_id)
    ).scalar_one()
    return (current or 0) + 1


def _evaluate_split(y_true: np.ndarray, y_prob: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 6),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 6),
        "roc_auc": None,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "row_count": int(len(y_true)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_prob)), 6)
    return metrics


def _build_lightgbm_importance(model: Any, feature_names: list[str]) -> list[dict[str, Any]]:
    scores = model.feature_importance(importance_type="gain")
    pairs = [
        {"feature": name, "importance": round(float(score), 6)}
        for name, score in zip(feature_names, scores, strict=True)
    ]
    pairs.sort(key=lambda item: item["importance"], reverse=True)
    return pairs


def _build_sklearn_importance(model: HistGradientBoostingClassifier, feature_names: list[str]) -> list[dict[str, Any]]:
    scores = model.feature_importances_
    pairs = [
        {"feature": name, "importance": round(float(score), 6)}
        for name, score in zip(feature_names, scores, strict=True)
    ]
    pairs.sort(key=lambda item: item["importance"], reverse=True)
    return pairs


def _load_lightgbm():
    try:
        import lightgbm as lgb
    except (OSError, FileNotFoundError, ImportError) as exc:
        return None, exc
    return lgb, None


def _train_lightgbm(
    lgb: Any,
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_val: np.ndarray,
    y_val: np.ndarray,
    feature_names: list[str],
    has_validation: bool,
) -> tuple[Any, str]:
    train_set = lgb.Dataset(x_train, label=y_train, feature_name=feature_names, free_raw_data=False)
    valid_sets = [train_set]
    valid_names = ["train"]
    if has_validation:
        valid_sets.append(lgb.Dataset(x_val, label=y_val, feature_name=feature_names, free_raw_data=False))
        valid_names.append("validation")

    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "learning_rate": 0.05,
        "num_leaves": 15,
        "feature_fraction": 0.9,
        "bagging_fraction": 0.9,
        "bagging_freq": 1,
        "verbosity": -1,
        "seed": RANDOM_SEED,
    }

    booster = lgb.train(
        params,
        train_set,
        num_boost_round=100,
        valid_sets=valid_sets,
        valid_names=valid_names,
    )
    return booster, "lightgbm"


def _train_sklearn_classifier(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
) -> tuple[HistGradientBoostingClassifier, str]:
    classifier = HistGradientBoostingClassifier(
        random_state=RANDOM_SEED,
        max_iter=100,
        learning_rate=0.05,
    )
    classifier.fit(x_train, y_train)
    return classifier, "sklearn_hist_gradient_boosting"


def _predict_scores(model: Any, x_values: np.ndarray, engine: str) -> np.ndarray:
    if len(x_values) == 0:
        return np.array([])
    if engine == "lightgbm":
        return model.predict(x_values)
    return model.predict_proba(x_values)[:, 1]


def train_model(
    db: Session,
    *,
    dataset_id: UUID,
    target_label: str,
    model_type: str,
    researcher_id: UUID | None,
) -> MLModel:
    if model_type not in SUPPORTED_MODEL_TYPES:
        raise TrainingError(f"Unsupported model_type '{model_type}'", status_code=422)
    if target_label not in SUPPORTED_TARGET_LABELS:
        raise TrainingError(f"Unsupported target_label '{target_label}'", status_code=422)

    dataset, rows = _load_training_rows(db, dataset_id)
    feature_names = _extract_feature_names(rows)
    if not feature_names:
        raise TrainingError("No numeric engineered features available for training", status_code=422)

    participant_ids = [row.participant_id for row in rows]
    train_participants, val_participants, test_participants = split_participants(participant_ids)

    train_rows = [row for row in rows if row.participant_id in train_participants]
    val_rows = [row for row in rows if row.participant_id in val_participants]
    test_rows = [row for row in rows if row.participant_id in test_participants]

    def labels_for(split_rows: list[MLDatasetRow]) -> tuple[np.ndarray, np.ndarray]:
        x_values = np.array([_row_to_vector(row.features, feature_names) for row in split_rows], dtype=float)
        y_values = np.array(
            [1 if row.labels.get(target_label) else 0 for row in split_rows],
            dtype=int,
        )
        return x_values, y_values

    x_train, y_train = labels_for(train_rows)
    x_val, y_val = labels_for(val_rows)
    x_test, y_test = labels_for(test_rows)

    if len(y_train) < 1:
        raise TrainingError("Training split has no target labels", status_code=422)

    lgb, lgb_error = _load_lightgbm()
    model = None
    engine = "sklearn_hist_gradient_boosting"
    build_importance = lambda trained: _build_sklearn_importance(trained, feature_names)
    artifact_name = "model.joblib"

    if lgb is not None and len(x_train) >= 2:
        try:
            model, engine = _train_lightgbm(
                lgb,
                x_train=x_train,
                y_train=y_train,
                x_val=x_val,
                y_val=y_val,
                feature_names=feature_names,
                has_validation=len(val_rows) > 0,
            )
            build_importance = lambda trained: _build_lightgbm_importance(trained, feature_names)
            artifact_name = "model.txt"
        except Exception as exc:
            lgb_error = exc
            model = None

    if model is None:
        model, engine = _train_sklearn_classifier(x_train=x_train, y_train=y_train)
        build_importance = lambda trained: _build_sklearn_importance(trained, feature_names)
        artifact_name = "model.joblib"

    val_metrics: dict[str, Any] | None = None
    if len(val_rows) > 0:
        val_prob = _predict_scores(model, x_val, engine)
        val_pred = (val_prob >= 0.5).astype(int)
        val_metrics = _evaluate_split(y_val, val_prob, val_pred)

    test_prob = _predict_scores(model, x_test, engine)
    test_pred = (test_prob >= 0.5).astype(int) if len(test_rows) > 0 else np.array([])
    test_metrics = _evaluate_split(y_test, test_prob, test_pred) if len(test_rows) > 0 else None

    train_prob = _predict_scores(model, x_train, engine)
    train_pred = (train_prob >= 0.5).astype(int)
    train_metrics = _evaluate_split(y_train, train_prob, train_pred)

    model_id = uuid.uuid4()
    model_version = _next_model_version(db, dataset_id)
    artifact_dir = MODELS_DIR / str(model_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_file = artifact_dir / artifact_name
    metadata_file = artifact_dir / "metadata.json"

    if engine == "lightgbm":
        model.save_model(str(model_file))
    else:
        joblib.dump(model, model_file)

    metrics_payload = {
        "target_label": target_label,
        "model_type": model_type,
        "dataset_version": dataset.dataset_version,
        "training_engine": engine,
        "lightgbm_load_error": str(lgb_error) if lgb is None and lgb_error is not None else None,
        "random_seed": RANDOM_SEED,
        "split_ratios": {
            "train": TRAIN_RATIO,
            "validation": VAL_RATIO,
            "test": TEST_RATIO,
        },
        "participant_counts": {
            "train": len(train_participants),
            "validation": len(val_participants),
            "test": len(test_participants),
            "total": len(set(participant_ids)),
        },
        "train_rows": len(train_rows),
        "validation_rows": len(val_rows),
        "test_rows": len(test_rows),
        "train": train_metrics,
        "validation": val_metrics,
        "test": test_metrics,
        "feature_count": len(feature_names),
    }

    feature_importance = build_importance(model)

    metadata_file.write_text(
        json.dumps(
            {
                "model_id": str(model_id),
                "dataset_id": str(dataset_id),
                "target_label": target_label,
                "model_type": model_type,
                "training_engine": engine,
                "feature_names": feature_names,
                "metrics": metrics_payload,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    model_record = MLModel(
        id=model_id,
        dataset_id=dataset_id,
        model_type=model_type,
        target_label=target_label,
        feature_schema_version=dataset.feature_schema_version,
        label_schema_version=dataset.label_schema_version,
        model_version=model_version,
        train_size=len(train_rows),
        validation_size=len(val_rows),
        test_size=len(test_rows),
        metrics=metrics_payload,
        feature_importance={"features": feature_importance},
        artifact_path=str(model_file.relative_to(MODELS_DIR.parent)),
        created_by_researcher_id=researcher_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(model_record)
    db.commit()
    db.refresh(model_record)
    return model_record


def list_models(db: Session) -> list[MLModel]:
    query = (
        select(MLModel)
        .join(MLDataset, MLModel.dataset_id == MLDataset.id)
        .order_by(MLModel.created_at.desc())
    )
    query = apply_dataset_filter(query)
    return db.execute(query).scalars().all()


def get_model(db: Session, model_id: UUID) -> MLModel:
    model = db.get(MLModel, model_id)
    if model is None:
        raise TrainingError("Model not found", status_code=404)
    try:
        assert_model_visible(db, model)
    except StudyGuardError as exc:
        raise TrainingError(exc.message, status_code=exc.status_code) from exc
    return model
