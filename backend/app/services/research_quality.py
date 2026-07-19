"""Dataset quality reporting for ML research datasets (Phase 2C)."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_row import MLDatasetRow
from app.services.research_correlations import get_numeric_feature_keys

LABEL_SCHEMA_VERSION = "1.0"


def _quality_score(
    *,
    completion_rate: float,
    valid_training_rate: float,
    duplicate_rate: float,
    imbalance_ratio: float,
    avg_missing_percent: float,
) -> float:
    duplicate_penalty = min(duplicate_rate * 100, 20.0)
    imbalance_penalty = min(max(0.0, imbalance_ratio - 1.0) * 10.0, 20.0)
    missing_penalty = min(avg_missing_percent, 30.0)
    score = (
        completion_rate * 0.35
        + valid_training_rate * 0.35
        + max(0.0, 100.0 - missing_penalty) * 0.15
        + max(0.0, 100.0 - duplicate_penalty) * 0.075
        + max(0.0, 100.0 - imbalance_penalty) * 0.075
    )
    return round(min(100.0, max(0.0, score)), 2)


def compute_quality_report(rows: list[MLDatasetRow], dataset: MLDataset) -> dict[str, Any]:
    total_rows = len(rows)
    numeric_keys = get_numeric_feature_keys(rows)

    row_keys = Counter((row.participant_id, row.session_date) for row in rows)
    duplicate_rows = sum(count - 1 for count in row_keys.values() if count > 1)

    rows_by_participant: dict[str, int] = defaultdict(int)
    complete_count = 0
    valid_training_count = 0
    burnout_labeled = 0
    burnout_true = 0
    dropout_true = 0
    missing_totals: dict[str, int] = {key: 0 for key in numeric_keys}

    for row in rows:
        rows_by_participant[str(row.participant_id)] += 1
        if row.quality_flags.get("complete_day"):
            complete_count += 1
        if row.labels.get("valid_training_row"):
            valid_training_count += 1
        if row.labels.get("burnout_next_day") is not None:
            burnout_labeled += 1
            if row.labels.get("burnout_next_day"):
                burnout_true += 1
        if row.labels.get("study_dropout"):
            dropout_true += 1

        for key in numeric_keys:
            value = row.features.get(key)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                missing_totals[key] += 1

    per_participant_counts = list(rows_by_participant.values())
    min_sessions = min(per_participant_counts) if per_participant_counts else 0
    max_sessions = max(per_participant_counts) if per_participant_counts else 0
    imbalance_ratio = (max_sessions / min_sessions) if min_sessions > 0 else 0.0

    missing_percents = [
        (missing_totals[key] / total_rows * 100) if total_rows else 0.0 for key in numeric_keys
    ]
    avg_missing_percent = sum(missing_percents) / len(missing_percents) if missing_percents else 0.0

    completion_rate = (complete_count / total_rows * 100) if total_rows else 0.0
    valid_training_rate = (valid_training_count / total_rows * 100) if total_rows else 0.0
    duplicate_rate = (duplicate_rows / total_rows) if total_rows else 0.0
    burnout_prevalence = (burnout_true / burnout_labeled * 100) if burnout_labeled else None
    dropout_prevalence = (dropout_true / total_rows * 100) if total_rows else 0.0

    return {
        "dataset_id": str(dataset.id),
        "dataset_version": dataset.dataset_version,
        "feature_schema_version": dataset.feature_schema_version,
        "label_schema_version": dataset.label_schema_version or LABEL_SCHEMA_VERSION,
        "schema_version": "1.0",
        "row_count": total_rows,
        "participant_count": dataset.participant_count,
        "missing_percentages": {
            key: round(missing_totals[key] / total_rows * 100, 4) if total_rows else 0.0
            for key in sorted(numeric_keys)
        },
        "average_missing_percent": round(avg_missing_percent, 4),
        "duplicate_rows": duplicate_rows,
        "duplicate_row_rate": round(duplicate_rate * 100, 4),
        "participant_imbalance": {
            "min_sessions_per_participant": min_sessions,
            "max_sessions_per_participant": max_sessions,
            "imbalance_ratio": round(imbalance_ratio, 4),
        },
        "sessions_per_participant": {
            str(participant_id): count for participant_id, count in rows_by_participant.items()
        },
        "valid_training_rows": valid_training_count,
        "valid_training_row_rate": round(valid_training_rate, 4),
        "burnout_prevalence_percent": round(burnout_prevalence, 4) if burnout_prevalence is not None else None,
        "dropout_prevalence_percent": round(dropout_prevalence, 4),
        "average_completion_rate": round(completion_rate, 4),
        "quality_score": _quality_score(
            completion_rate=completion_rate,
            valid_training_rate=valid_training_rate,
            duplicate_rate=duplicate_rate,
            imbalance_ratio=imbalance_ratio,
            avg_missing_percent=avg_missing_percent,
        ),
    }
