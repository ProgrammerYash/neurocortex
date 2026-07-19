from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_row import MLDatasetRow
from app.schemas.ml import DatasetSummary
from app.services.research_etl import build_research_dataset, summarize_dataset
from app.services.research_labeling import (
    generate_dataset_labels,
    get_labels_summary,
    get_latest_artifact,
)
from app.services.study_guard import StudyGuardError, apply_dataset_filter, assert_dataset_visible


class DatasetError(Exception):
    def __init__(self, message: str, status_code: int = 404):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def create_dataset(
    db: Session,
    *,
    researcher_id: UUID | None,
    name: str | None,
    dataset_mode: str = "strict",
) -> MLDataset:
    return build_research_dataset(
        db,
        researcher_id=researcher_id,
        name=name,
        dataset_mode=dataset_mode,
    )


def list_datasets(db: Session) -> list[MLDataset]:
    query = apply_dataset_filter(
        select(MLDataset).order_by(MLDataset.created_at.desc())
    )
    return db.execute(query).scalars().all()


def get_dataset(db: Session, dataset_id: UUID) -> MLDataset:
    dataset = db.get(MLDataset, dataset_id)
    if dataset is None:
        raise DatasetError("Dataset not found", status_code=404)
    try:
        assert_dataset_visible(dataset)
    except StudyGuardError as exc:
        raise DatasetError(exc.message, status_code=exc.status_code) from exc
    return dataset


def get_dataset_summary(db: Session, dataset_id: UUID) -> DatasetSummary:
    get_dataset(db, dataset_id)
    summary = summarize_dataset(db, dataset_id)
    return DatasetSummary(**summary)


def list_dataset_rows(
    db: Session,
    dataset_id: UUID,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[MLDatasetRow], int]:
    get_dataset(db, dataset_id)
    total = db.execute(
        select(func.count())
        .select_from(MLDatasetRow)
        .where(MLDatasetRow.dataset_id == dataset_id)
    ).scalar_one()
    rows = db.execute(
        select(MLDatasetRow)
        .where(MLDatasetRow.dataset_id == dataset_id)
        .order_by(MLDatasetRow.session_date.asc(), MLDatasetRow.public_id.asc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return rows, total


def label_dataset(db: Session, dataset_id: UUID) -> dict:
    get_dataset(db, dataset_id)
    try:
        return generate_dataset_labels(db, dataset_id)
    except ValueError as exc:
        raise DatasetError(str(exc), status_code=404) from exc


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _artifact_to_response(artifact: dict | None) -> dict:
    if artifact is None:
        return {}
    response = dict(artifact)
    response["dataset_id"] = UUID(response["dataset_id"])
    if "created_at" in response and isinstance(response["created_at"], str):
        response["created_at"] = _parse_datetime(response["created_at"])
    if "generated_at" in response and isinstance(response["generated_at"], str):
        response["generated_at"] = _parse_datetime(response["generated_at"])
    return response


def get_dataset_statistics(db: Session, dataset_id: UUID) -> dict:
    get_dataset(db, dataset_id)
    artifact = get_latest_artifact(db, dataset_id, "statistics")
    if artifact is None:
        raise DatasetError(
            "Statistics not available. Generate labels first via POST /datasets/{id}/label",
            status_code=404,
        )
    return _artifact_to_response(artifact)


def get_dataset_correlations(db: Session, dataset_id: UUID) -> dict:
    get_dataset(db, dataset_id)
    artifact = get_latest_artifact(db, dataset_id, "correlations")
    if artifact is None:
        raise DatasetError(
            "Correlations not available. Generate labels first via POST /datasets/{id}/label",
            status_code=404,
        )
    return _artifact_to_response(artifact)


def get_dataset_quality(db: Session, dataset_id: UUID) -> dict:
    get_dataset(db, dataset_id)
    artifact = get_latest_artifact(db, dataset_id, "quality")
    if artifact is None:
        raise DatasetError(
            "Quality report not available. Generate labels first via POST /datasets/{id}/label",
            status_code=404,
        )
    return _artifact_to_response(artifact)


def get_dataset_labels(db: Session, dataset_id: UUID) -> dict:
    get_dataset(db, dataset_id)
    try:
        return _artifact_to_response(get_labels_summary(db, dataset_id))
    except ValueError as exc:
        raise DatasetError(str(exc), status_code=404) from exc
