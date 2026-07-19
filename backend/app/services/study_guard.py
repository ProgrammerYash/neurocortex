"""Central Study Mode policy for NeuroCortex pilot/production deployments."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import or_, select

from app.config import Settings, get_settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.ml_dataset import MLDataset
    from app.models.ml_model import MLModel
    from app.models.participant import Participant


class StudyGuardError(Exception):
    def __init__(self, message: str, status_code: int = 404):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _settings() -> Settings:
    return get_settings()


def get_synthetic_prefixes() -> list[str]:
    raw = _settings().block_synthetic_prefixes.strip()
    if not raw:
        return []
    return [prefix.strip() for prefix in raw.split(",") if prefix.strip()]


def get_synthetic_dataset_prefix() -> str:
    return _settings().synthetic_dataset_prefix.strip()


def should_show_test_data() -> bool:
    return _settings().show_test_data


def should_show_experimental_banner() -> bool:
    return _settings().study_mode == "pilot"


def allow_participant_predictions() -> bool:
    return _settings().allow_participant_predictions


def is_synthetic_public_id(public_id: str | None) -> bool:
    if not public_id:
        return False
    normalized = public_id.strip().upper()
    return any(normalized.startswith(prefix.upper()) for prefix in get_synthetic_prefixes())


def is_synthetic_dataset_name(name: str | None) -> bool:
    if not name:
        return False
    prefix = get_synthetic_dataset_prefix()
    if not prefix:
        return False
    return name.strip().lower().startswith(prefix.lower())


def is_synthetic_participant(participant: Participant) -> bool:
    return is_synthetic_public_id(participant.public_id)


def is_synthetic_dataset(dataset: MLDataset) -> bool:
    return is_synthetic_dataset_name(dataset.name)


def should_filter_synthetic_data() -> bool:
    return not should_show_test_data()


def participant_visibility_clause():
    if not should_filter_synthetic_data():
        return None
    prefixes = get_synthetic_prefixes()
    if not prefixes:
        return None
    from app.models.participant import Participant

    return ~or_(*[Participant.public_id.ilike(f"{prefix}%") for prefix in prefixes])


def dataset_visibility_clause():
    if not should_filter_synthetic_data():
        return None
    prefix = get_synthetic_dataset_prefix()
    if not prefix:
        return None
    from app.models.ml_dataset import MLDataset

    return ~MLDataset.name.ilike(f"{prefix}%")


def apply_participant_filter(query):
    clause = participant_visibility_clause()
    if clause is not None:
        query = query.where(clause)
    return query


def apply_dataset_filter(query):
    clause = dataset_visibility_clause()
    if clause is not None:
        query = query.where(clause)
    return query


def assert_participant_visible(participant: Participant) -> None:
    if should_filter_synthetic_data() and is_synthetic_participant(participant):
        raise StudyGuardError("Participant not found", status_code=404)


def assert_dataset_visible(dataset: MLDataset) -> None:
    if should_filter_synthetic_data() and is_synthetic_dataset(dataset):
        raise StudyGuardError("Dataset not found", status_code=404)


def assert_model_visible(db: Session, model: MLModel) -> None:
    if not should_filter_synthetic_data():
        return
    from app.models.ml_dataset import MLDataset

    dataset = db.get(MLDataset, model.dataset_id)
    if dataset is None:
        raise StudyGuardError("Model not found", status_code=404)
    assert_dataset_visible(dataset)


def assert_prediction_participant_visible(db: Session, participant_id: UUID) -> None:
    if not should_filter_synthetic_data():
        return
    from app.models.participant import Participant

    participant = db.get(Participant, participant_id)
    if participant is None:
        raise StudyGuardError("Prediction not found", status_code=404)
    assert_participant_visible(participant)


def ensure_participant_predictions_allowed(*, role: str) -> None:
    if role == "participant" and not allow_participant_predictions():
        raise StudyGuardError(
            "Participant predictions are disabled in the current study mode",
            status_code=403,
        )


def visible_participant_ids(db: Session) -> set[UUID] | None:
    if not should_filter_synthetic_data():
        return None
    from app.models.participant import Participant

    query = apply_participant_filter(select(Participant.id))
    return set(db.execute(query).scalars().all())


def visible_dataset_ids(db: Session) -> set[UUID] | None:
    if not should_filter_synthetic_data():
        return None
    from app.models.ml_dataset import MLDataset

    query = apply_dataset_filter(select(MLDataset.id))
    return set(db.execute(query).scalars().all())


def get_study_config() -> dict[str, object]:
    settings = _settings()
    return {
        "study_mode": settings.study_mode,
        "show_test_data": should_show_test_data(),
        "allow_participant_predictions": allow_participant_predictions(),
        "show_experimental_banner": should_show_experimental_banner(),
        "block_synthetic_prefixes": get_synthetic_prefixes(),
        "synthetic_dataset_prefix": get_synthetic_dataset_prefix(),
        "filter_synthetic_data": should_filter_synthetic_data(),
    }
