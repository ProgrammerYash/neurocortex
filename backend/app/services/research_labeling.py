"""Research label generation for ML dataset rows (Phase 2C)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_artifact import MLDatasetArtifact
from app.models.ml_dataset_row import MLDatasetRow
from app.services.research_correlations import compute_correlations
from app.services.research_quality import compute_quality_report
from app.services.research_statistics import compute_descriptive_statistics

LABEL_SCHEMA_VERSION = "1.0"
TLX_THRESHOLD = 75.0
DROPOUT_GAP_DAYS = 7

BURNOUT_STRESS_MIN = 8.0
BURNOUT_FATIGUE_MIN = 8.0
BURNOUT_MOTIVATION_MAX = 3.0


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _burnout_next_day_from_features(next_features: dict[str, Any]) -> bool | None:
    stress = _to_float(next_features.get("survey_stress"))
    fatigue = _to_float(next_features.get("survey_fatigue"))
    motivation = _to_float(next_features.get("survey_motivation"))
    if stress is None or fatigue is None or motivation is None:
        return None
    return stress >= BURNOUT_STRESS_MIN and fatigue >= BURNOUT_FATIGUE_MIN and motivation <= BURNOUT_MOTIVATION_MAX


def _high_workload_next_day_from_features(next_features: dict[str, Any]) -> bool | None:
    tlx = _to_float(next_features.get("nasa_tlx_tlxScore"))
    if tlx is None:
        return None
    return tlx >= TLX_THRESHOLD


def _days_without_session_after(session_date: date, next_session_date: date | None, reference_date: date) -> int:
    if next_session_date is not None:
        return (next_session_date - session_date).days - 1
    return (reference_date - session_date).days


def _compute_row_labels(
    *,
    row: MLDatasetRow,
    next_row: MLDatasetRow | None,
    next_session_date: date | None,
    reference_date: date,
) -> dict[str, Any]:
    next_day_exists = next_row is not None
    burnout_next_day: bool | None = None
    high_workload_next_day: bool | None = None

    if next_row is not None:
        burnout_next_day = _burnout_next_day_from_features(next_row.features)
        high_workload_next_day = _high_workload_next_day_from_features(next_row.features)

    gap_days = _days_without_session_after(row.session_date, next_session_date, reference_date)
    study_dropout = gap_days >= DROPOUT_GAP_DAYS

    complete_day = bool(row.quality_flags.get("complete_day"))
    burnout_label_exists = burnout_next_day is not None
    valid_training_row = complete_day and burnout_label_exists and next_day_exists

    return {
        "burnout_next_day": burnout_next_day,
        "high_workload_next_day": high_workload_next_day,
        "study_dropout": study_dropout,
        "valid_training_row": valid_training_row,
        "label_schema_version": LABEL_SCHEMA_VERSION,
        "next_day_exists": next_day_exists,
        "days_until_next_session": (
            (next_session_date - row.session_date).days if next_session_date is not None else None
        ),
    }


def _load_rows_by_participant(rows: list[MLDatasetRow]) -> dict[UUID, list[MLDatasetRow]]:
    grouped: dict[UUID, list[MLDatasetRow]] = defaultdict(list)
    for row in rows:
        grouped[row.participant_id].append(row)
    for participant_rows in grouped.values():
        participant_rows.sort(key=lambda item: item.session_date)
    return grouped


def generate_dataset_labels(db: Session, dataset_id: UUID) -> dict[str, Any]:
    dataset = db.get(MLDataset, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found")

    rows = db.execute(
        select(MLDatasetRow)
        .where(MLDatasetRow.dataset_id == dataset_id)
        .order_by(MLDatasetRow.participant_id.asc(), MLDatasetRow.session_date.asc())
    ).scalars().all()

    grouped = _load_rows_by_participant(rows)
    reference_date = dataset.date_range_end or datetime.now(timezone.utc).date()

    labeled_count = 0
    for participant_rows in grouped.values():
        for index, row in enumerate(participant_rows):
            next_row = participant_rows[index + 1] if index + 1 < len(participant_rows) else None
            next_session_date = next_row.session_date if next_row is not None else None
            row.labels = _compute_row_labels(
                row=row,
                next_row=next_row,
                next_session_date=next_session_date,
                reference_date=reference_date,
            )
            labeled_count += 1

    now = datetime.now(timezone.utc)
    dataset.label_schema_version = LABEL_SCHEMA_VERSION
    dataset.labels_generated_at = now

    statistics_payload = compute_descriptive_statistics(rows, dataset)
    correlations_payload = compute_correlations(rows, dataset)
    quality_payload = compute_quality_report(rows, dataset)
    labels_summary_payload = _build_labels_summary(rows, dataset, now)

    _store_artifact(db, dataset_id, "statistics", statistics_payload)
    _store_artifact(db, dataset_id, "correlations", correlations_payload)
    _store_artifact(db, dataset_id, "quality", quality_payload)
    _store_artifact(db, dataset_id, "labels", labels_summary_payload)

    db.commit()
    db.refresh(dataset)

    return labels_summary_payload


def _build_labels_summary(
    rows: list[MLDatasetRow],
    dataset: MLDataset,
    generated_at: datetime,
) -> dict[str, Any]:
    def label_count(key: str, *, value: bool | None = None) -> int:
        if value is None:
            return sum(1 for row in rows if row.labels.get(key) is not None)
        return sum(1 for row in rows if row.labels.get(key) is value)

    burnout_labeled = [row for row in rows if row.labels.get("burnout_next_day") is not None]
    burnout_positive = sum(1 for row in burnout_labeled if row.labels.get("burnout_next_day") is True)

    return {
        "dataset_id": str(dataset.id),
        "dataset_version": dataset.dataset_version,
        "feature_schema_version": dataset.feature_schema_version,
        "label_schema_version": LABEL_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "row_count": len(rows),
        "labeled_rows": len(rows),
        "burnout_next_day_labeled": label_count("burnout_next_day"),
        "burnout_next_day_true": label_count("burnout_next_day", value=True),
        "burnout_next_day_false": label_count("burnout_next_day", value=False),
        "burnout_prevalence": (
            round(burnout_positive / len(burnout_labeled), 4) if burnout_labeled else None
        ),
        "high_workload_next_day_true": label_count("high_workload_next_day", value=True),
        "study_dropout_true": label_count("study_dropout", value=True),
        "valid_training_rows": label_count("valid_training_row", value=True),
    }


def _next_artifact_version(db: Session, dataset_id: UUID, artifact_type: str) -> int:
    current = db.execute(
        select(func.max(MLDatasetArtifact.artifact_version))
        .where(MLDatasetArtifact.dataset_id == dataset_id)
        .where(MLDatasetArtifact.artifact_type == artifact_type)
    ).scalar_one()
    return (current or 0) + 1


def _store_artifact(
    db: Session,
    dataset_id: UUID,
    artifact_type: str,
    payload: dict[str, Any],
) -> MLDatasetArtifact:
    version = _next_artifact_version(db, dataset_id, artifact_type)
    schema_version = payload.get("label_schema_version") or payload.get("schema_version") or LABEL_SCHEMA_VERSION
    artifact = MLDatasetArtifact(
        dataset_id=dataset_id,
        artifact_type=artifact_type,
        artifact_version=version,
        schema_version=str(schema_version),
        payload=payload,
    )
    db.add(artifact)
    return artifact


def get_latest_artifact(db: Session, dataset_id: UUID, artifact_type: str) -> dict[str, Any] | None:
    artifact = db.execute(
        select(MLDatasetArtifact)
        .where(MLDatasetArtifact.dataset_id == dataset_id)
        .where(MLDatasetArtifact.artifact_type == artifact_type)
        .order_by(MLDatasetArtifact.artifact_version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if artifact is None:
        return None
    return {
        "artifact_version": artifact.artifact_version,
        "schema_version": artifact.schema_version,
        "created_at": artifact.created_at.isoformat(),
        **artifact.payload,
    }


def get_labels_summary(db: Session, dataset_id: UUID) -> dict[str, Any]:
    dataset = db.get(MLDataset, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found")

    cached = get_latest_artifact(db, dataset_id, "labels")
    if cached is not None:
        return cached

    rows = db.execute(
        select(MLDatasetRow).where(MLDatasetRow.dataset_id == dataset_id)
    ).scalars().all()
    if not rows or dataset.labels_generated_at is None:
        raise ValueError("Labels have not been generated for this dataset")

    return _build_labels_summary(rows, dataset, dataset.labels_generated_at)
