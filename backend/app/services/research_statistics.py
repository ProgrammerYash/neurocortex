"""Descriptive statistics for ML research datasets (Phase 2C)."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any

from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_row import MLDatasetRow
from app.services.research_correlations import get_numeric_feature_keys

LABEL_SCHEMA_VERSION = "1.0"


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _feature_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "missing_count": None,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "median": None,
            "q1": None,
            "q3": None,
        }

    sorted_values = sorted(values)
    q1 = statistics.quantiles(sorted_values, n=4)[0] if len(sorted_values) >= 4 else sorted_values[0]
    q3 = statistics.quantiles(sorted_values, n=4)[2] if len(sorted_values) >= 4 else sorted_values[-1]
    std = statistics.stdev(sorted_values) if len(sorted_values) > 1 else 0.0

    return {
        "count": len(values),
        "mean": round(statistics.mean(sorted_values), 6),
        "std": round(std, 6),
        "min": round(min(sorted_values), 6),
        "max": round(max(sorted_values), 6),
        "median": round(statistics.median(sorted_values), 6),
        "q1": round(q1, 6),
        "q3": round(q3, 6),
    }


def compute_descriptive_statistics(
    rows: list[MLDatasetRow],
    dataset: MLDataset,
) -> dict[str, Any]:
    numeric_keys = get_numeric_feature_keys(rows)
    total_rows = len(rows)

    rows_by_participant: dict[str, int] = defaultdict(int)
    session_dates: list[Any] = []
    complete_count = 0
    valid_training_count = 0

    feature_values: dict[str, list[float]] = {key: [] for key in numeric_keys}
    missing_counts: dict[str, int] = {key: 0 for key in numeric_keys}

    for row in rows:
        rows_by_participant[str(row.participant_id)] += 1
        session_dates.append(row.session_date)
        if row.quality_flags.get("complete_day"):
            complete_count += 1
        if row.labels.get("valid_training_row"):
            valid_training_count += 1

        for key in numeric_keys:
            value = row.features.get(key)
            if _is_number(value):
                feature_values[key].append(float(value))
            else:
                missing_counts[key] += 1

    per_participant_counts = list(rows_by_participant.values())
    avg_sessions = (
        round(statistics.mean(per_participant_counts), 4) if per_participant_counts else 0.0
    )

    study_duration_days: float | None = None
    if session_dates:
        study_duration_days = (max(session_dates) - min(session_dates)).days + 1

    feature_statistics = {
        key: {
            **_feature_stats(feature_values[key]),
            "missing_count": missing_counts[key],
            "missing_percent": round(missing_counts[key] / total_rows * 100, 4) if total_rows else 0.0,
        }
        for key in sorted(numeric_keys)
    }

    return {
        "dataset_id": str(dataset.id),
        "dataset_version": dataset.dataset_version,
        "feature_schema_version": dataset.feature_schema_version,
        "label_schema_version": dataset.label_schema_version or LABEL_SCHEMA_VERSION,
        "schema_version": "1.0",
        "participant_count": dataset.participant_count,
        "row_count": total_rows,
        "rows_per_participant": {
            "mean": avg_sessions,
            "min": min(per_participant_counts) if per_participant_counts else 0,
            "max": max(per_participant_counts) if per_participant_counts else 0,
            "median": round(statistics.median(per_participant_counts), 4) if per_participant_counts else 0,
        },
        "study_duration_days": study_duration_days,
        "average_sessions_per_participant": avg_sessions,
        "completion_rate": round(complete_count / total_rows * 100, 4) if total_rows else 0.0,
        "valid_training_row_count": valid_training_count,
        "missing_values_per_feature": {
            key: {
                "count": missing_counts[key],
                "percent": round(missing_counts[key] / total_rows * 100, 4) if total_rows else 0.0,
            }
            for key in sorted(numeric_keys)
        },
        "feature_statistics": feature_statistics,
    }
