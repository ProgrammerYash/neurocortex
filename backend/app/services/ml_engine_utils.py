"""Shared ML inference helpers (no training)."""

from __future__ import annotations

from typing import Any

import numpy as np


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def row_to_vector(features: dict[str, Any], feature_names: list[str]) -> list[float]:
    vector: list[float] = []
    for name in feature_names:
        value = features.get(name)
        if is_number(value):
            vector.append(float(value))
        else:
            vector.append(float("nan"))
    return vector


def predict_scores(model: Any, x_values: np.ndarray, engine: str) -> np.ndarray:
    if len(x_values) == 0:
        return np.array([])
    if engine == "lightgbm":
        return model.predict(x_values)
    return model.predict_proba(x_values)[:, 1]
