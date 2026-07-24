"""Load and run the fixed pretrained model artifact (inference only)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from app.services.ml_engine_utils import predict_scores, row_to_vector

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "model_artifacts"
MANIFEST_PATH = ARTIFACTS_DIR / "model_manifest.json"


class FixedModelError(Exception):
    def __init__(self, message: str, *, configured: bool = False):
        self.message = message
        self.configured = configured
        super().__init__(message)


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise FixedModelError("Model manifest not found", configured=False)
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def model_is_configured() -> bool:
    try:
        manifest = load_manifest()
    except FixedModelError:
        return False
    artifact = ARTIFACTS_DIR / str(manifest.get("artifact_filename", ""))
    feature_names = manifest.get("feature_names") or []
    return artifact.exists() and len(feature_names) > 0


@lru_cache(maxsize=1)
def _load_engine() -> tuple[Any, dict[str, Any]]:
    manifest = load_manifest()
    artifact = ARTIFACTS_DIR / str(manifest["artifact_filename"])
    if not artifact.exists():
        raise FixedModelError("Fixed model artifact is not configured", configured=False)
    feature_names = manifest.get("feature_names") or []
    if not feature_names:
        raise FixedModelError("Fixed model feature list is empty", configured=False)
    engine = joblib.load(artifact)
    return engine, manifest


def clear_fixed_model_cache() -> None:
    _load_engine.cache_clear()
    load_manifest.cache_clear()


def category_from_probability(probability: float, manifest: dict[str, Any]) -> tuple[str, str]:
    thresholds = manifest.get("category_thresholds") or {}
    low_max = float(thresholds.get("low_max", 0.35))
    elevated_min = float(thresholds.get("elevated_min", 0.7))
    probability = max(0.0, min(1.0, probability))
    if probability < low_max:
        return "low", "Low estimated cognitive strain"
    if probability >= elevated_min:
        return "elevated", "Elevated estimated cognitive strain"
    return "moderate", "Moderate estimated cognitive strain"


def run_fixed_model_inference(features: dict[str, Any]) -> tuple[float, str, str, str]:
    engine, manifest = _load_engine()
    feature_names = manifest["feature_names"]
    vector = np.array([row_to_vector(features, feature_names)], dtype=float)
    if np.isnan(vector).all():
        raise FixedModelError("No usable model features", configured=True)
    probability = float(predict_scores(engine, vector, "sklearn_hist_gradient_boosting")[0])
    category, label = category_from_probability(probability, manifest)
    return probability, category, label, str(manifest.get("model_version", "unknown"))
