"""Feature correlation analysis for ML research datasets (Phase 2C)."""

from __future__ import annotations

import math
from typing import Any

from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_row import MLDatasetRow

LABEL_SCHEMA_VERSION = "1.0"

NON_NUMERIC_FEATURE_KEYS = frozenset(
    {
        "participant_public_id",
        "session_date",
        "participant_grade",
        "participant_age_range",
        "participant_joined_at",
        "session_complete",
        "survey_exam",
    }
)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def get_numeric_feature_keys(rows: list[MLDatasetRow]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        for key, value in row.features.items():
            if key in NON_NUMERIC_FEATURE_KEYS:
                continue
            if _is_number(value):
                keys.add(key)
    return sorted(keys)


def _rank_values(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        start = index
        value = indexed[index][1]
        while index + 1 < len(indexed) and indexed[index + 1][1] == value:
            index += 1
        end = index
        avg_rank = (start + end) / 2.0 + 1.0
        for position in range(start, end + 1):
            original_index = indexed[position][0]
            ranks[original_index] = avg_rank
        index += 1
    return ranks


def _pearson(x_values: list[float], y_values: list[float]) -> float | None:
    n = len(x_values)
    if n < 2:
        return None

    mean_x = sum(x_values) / n
    mean_y = sum(y_values) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_values))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_values))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def _aligned_pairs(
    rows: list[MLDatasetRow],
    feature_a: str,
    feature_b: str,
) -> tuple[list[float], list[float]]:
    x_values: list[float] = []
    y_values: list[float] = []
    for row in rows:
        a = row.features.get(feature_a)
        b = row.features.get(feature_b)
        if _is_number(a) and _is_number(b):
            x_values.append(float(a))
            y_values.append(float(b))
    return x_values, y_values


def compute_correlations(rows: list[MLDatasetRow], dataset: MLDataset) -> dict[str, Any]:
    numeric_keys = get_numeric_feature_keys(rows)
    pairs: list[dict[str, Any]] = []

    for index, feature_a in enumerate(numeric_keys):
        for feature_b in numeric_keys[index + 1 :]:
            x_values, y_values = _aligned_pairs(rows, feature_a, feature_b)
            sample_count = len(x_values)
            pearson = _pearson(x_values, y_values) if sample_count >= 2 else None
            spearman = None
            if sample_count >= 2:
                rank_x = _rank_values(x_values)
                rank_y = _rank_values(y_values)
                spearman = _pearson(rank_x, rank_y)

            pairs.append(
                {
                    "feature_a": feature_a,
                    "feature_b": feature_b,
                    "pearson": round(pearson, 6) if pearson is not None else None,
                    "spearman": round(spearman, 6) if spearman is not None else None,
                    "sample_count": sample_count,
                }
            )

    return {
        "dataset_id": str(dataset.id),
        "dataset_version": dataset.dataset_version,
        "feature_schema_version": dataset.feature_schema_version,
        "label_schema_version": dataset.label_schema_version or LABEL_SCHEMA_VERSION,
        "schema_version": "1.0",
        "feature_count": len(numeric_keys),
        "pair_count": len(pairs),
        "pairs": pairs,
    }
