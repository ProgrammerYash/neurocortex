"""Remove synthetic integration-test data before a real pilot study."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, or_, select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.daily_session import DailySession  # noqa: E402
from app.models.ml_dataset import MLDataset  # noqa: E402
from app.models.ml_dataset_artifact import MLDatasetArtifact  # noqa: E402
from app.models.ml_dataset_row import MLDatasetRow  # noqa: E402
from app.models.ml_explanation import MLExplanation  # noqa: E402
from app.models.ml_model import MLModel  # noqa: E402
from app.models.ml_prediction import MLPrediction  # noqa: E402
from app.models.module_result import ModuleResult  # noqa: E402
from app.models.participant import Participant  # noqa: E402
from app.models.participant_game_data import ParticipantGameData  # noqa: E402
from app.services.ml_training import MODELS_DIR  # noqa: E402
from app.services.study_guard import (  # noqa: E402
    get_synthetic_dataset_prefix,
    get_synthetic_prefixes,
    is_synthetic_dataset_name,
)


class PurgeReport:
    def __init__(self) -> None:
        self.participants = 0
        self.sessions = 0
        self.module_results = 0
        self.game_data = 0
        self.datasets = 0
        self.dataset_rows = 0
        self.dataset_artifacts = 0
        self.models = 0
        self.predictions = 0
        self.explanations = 0
        self.artifact_folders = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "participants_removed": self.participants,
            "sessions_removed": self.sessions,
            "module_results_removed": self.module_results,
            "game_data_removed": self.game_data,
            "datasets_removed": self.datasets,
            "dataset_rows_removed": self.dataset_rows,
            "dataset_artifacts_removed": self.dataset_artifacts,
            "models_removed": self.models,
            "predictions_removed": self.predictions,
            "explanations_removed": self.explanations,
            "artifact_folders_removed": self.artifact_folders,
        }


def _participant_prefix_filters():
    prefixes = get_synthetic_prefixes()
    return [Participant.public_id.ilike(f"{prefix}%") for prefix in prefixes]


def _collect_targets(db) -> dict[str, set]:
    participant_filters = _participant_prefix_filters()
    synthetic_participants = set()
    if participant_filters:
        synthetic_participants = set(
            db.execute(
                select(Participant.id).where(or_(*participant_filters))
            ).scalars().all()
        )

    datasets = db.execute(select(MLDataset.id, MLDataset.name)).all()
    synthetic_datasets = {
        dataset_id
        for dataset_id, name in datasets
        if is_synthetic_dataset_name(name)
    }

    models = db.execute(select(MLModel.id, MLModel.dataset_id)).all()
    synthetic_models = {
        model_id
        for model_id, dataset_id in models
        if dataset_id in synthetic_datasets
    }

    predictions = db.execute(
        select(MLPrediction.id, MLPrediction.participant_id, MLPrediction.model_id)
    ).all()
    synthetic_predictions = {
        prediction_id
        for prediction_id, participant_id, model_id in predictions
        if participant_id in synthetic_participants or model_id in synthetic_models
    }

    explanations = db.execute(
        select(MLExplanation.id, MLExplanation.participant_id, MLExplanation.model_id)
    ).all()
    synthetic_explanations = {
        explanation_id
        for explanation_id, participant_id, model_id in explanations
        if participant_id in synthetic_participants or model_id in synthetic_models
    }

    dataset_rows = db.execute(
        select(MLDatasetRow.id, MLDatasetRow.dataset_id, MLDatasetRow.participant_id)
    ).all()
    synthetic_dataset_rows = {
        row_id
        for row_id, dataset_id, participant_id in dataset_rows
        if dataset_id in synthetic_datasets or participant_id in synthetic_participants
    }

    dataset_artifacts = db.execute(
        select(MLDatasetArtifact.id, MLDatasetArtifact.dataset_id)
    ).all()
    synthetic_dataset_artifacts = {
        artifact_id
        for artifact_id, dataset_id in dataset_artifacts
        if dataset_id in synthetic_datasets
    }

    sessions = db.execute(
        select(DailySession.id, DailySession.participant_id)
    ).all()
    synthetic_sessions = {
        session_id
        for session_id, participant_id in sessions
        if participant_id in synthetic_participants
    }

    module_results = db.execute(
        select(ModuleResult.id, ModuleResult.session_id)
    ).all()
    synthetic_module_results = {
        module_id
        for module_id, session_id in module_results
        if session_id in synthetic_sessions
    }

    game_data = db.execute(
        select(ParticipantGameData.id, ParticipantGameData.participant_id)
    ).all()
    synthetic_game_data = {
        record_id
        for record_id, participant_id in game_data
        if participant_id in synthetic_participants
    }

    return {
        "participants": synthetic_participants,
        "datasets": synthetic_datasets,
        "models": synthetic_models,
        "predictions": synthetic_predictions,
        "explanations": synthetic_explanations,
        "dataset_rows": synthetic_dataset_rows,
        "dataset_artifacts": synthetic_dataset_artifacts,
        "sessions": synthetic_sessions,
        "module_results": synthetic_module_results,
        "game_data": synthetic_game_data,
    }


def build_report(db) -> PurgeReport:
    targets = _collect_targets(db)
    report = PurgeReport()
    report.participants = len(targets["participants"])
    report.sessions = len(targets["sessions"])
    report.module_results = len(targets["module_results"])
    report.game_data = len(targets["game_data"])
    report.datasets = len(targets["datasets"])
    report.dataset_rows = len(targets["dataset_rows"])
    report.dataset_artifacts = len(targets["dataset_artifacts"])
    report.models = len(targets["models"])
    report.predictions = len(targets["predictions"])
    report.explanations = len(targets["explanations"])
    report.artifact_folders = len(targets["models"])
    return report


def purge_test_data(*, execute: bool) -> PurgeReport:
    db = SessionLocal()
    report = build_report(db)
    if not execute:
        db.close()
        return report

    targets = _collect_targets(db)
    try:
        if targets["explanations"]:
            db.execute(
                delete(MLExplanation).where(MLExplanation.id.in_(targets["explanations"]))
            )
        if targets["predictions"]:
            db.execute(
                delete(MLPrediction).where(MLPrediction.id.in_(targets["predictions"]))
            )
        if targets["models"]:
            db.execute(delete(MLModel).where(MLModel.id.in_(targets["models"])))
        if targets["dataset_artifacts"]:
            db.execute(
                delete(MLDatasetArtifact).where(
                    MLDatasetArtifact.id.in_(targets["dataset_artifacts"])
                )
            )
        if targets["dataset_rows"]:
            db.execute(
                delete(MLDatasetRow).where(MLDatasetRow.id.in_(targets["dataset_rows"]))
            )
        if targets["datasets"]:
            db.execute(delete(MLDataset).where(MLDataset.id.in_(targets["datasets"])))
        if targets["module_results"]:
            db.execute(
                delete(ModuleResult).where(ModuleResult.id.in_(targets["module_results"]))
            )
        if targets["sessions"]:
            db.execute(delete(DailySession).where(DailySession.id.in_(targets["sessions"])))
        if targets["game_data"]:
            db.execute(
                delete(ParticipantGameData).where(
                    ParticipantGameData.id.in_(targets["game_data"])
                )
            )
        if targets["participants"]:
            db.execute(
                delete(Participant).where(Participant.id.in_(targets["participants"]))
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    for model_id in targets["models"]:
        artifact_dir = MODELS_DIR / str(model_id)
        if artifact_dir.exists() and artifact_dir.is_dir():
            shutil.rmtree(artifact_dir, ignore_errors=True)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Purge synthetic NeuroCortex test data")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform deletion. Without this flag the script runs in dry-run mode.",
    )
    args = parser.parse_args()

    settings = get_settings()
    print("Study mode:", settings.study_mode)
    print("Synthetic participant prefixes:", ", ".join(get_synthetic_prefixes()) or "(none)")
    print("Synthetic dataset prefix:", get_synthetic_dataset_prefix() or "(none)")
    print("Mode:", "EXECUTE" if args.execute else "DRY-RUN")
    print()

    report = purge_test_data(execute=args.execute)
    for key, value in report.as_dict().items():
        print(f"{key}: {value}")

    if not args.execute:
        print()
        print("Dry-run complete. Re-run with --execute to delete the items above.")


if __name__ == "__main__":
    main()
