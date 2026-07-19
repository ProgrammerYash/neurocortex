"""Research ETL: flatten raw PostgreSQL data into participant-day feature rows."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.daily_session import SESSION_STATUS_COMPLETE, DailySession
from app.models.ml_dataset import MLDataset
from app.models.ml_dataset_row import MLDatasetRow
from app.models.participant import Participant
from app.models.session_data_quality_flag import SessionDataQualityFlag
from app.services.study_guard import apply_participant_filter, is_synthetic_public_id
from app.services.consent_service import consent_eligible_at_session_time
from app.services.data_quality_service import session_has_reviewed_exclude, session_has_unresolved_critical_flags
from app.services.procedure_service import resolve_active_procedure

FEATURE_SCHEMA_VERSION = "1.0"

REACTION_FIELDS = ("avg", "median", "sd", "min", "max", "missed")
TYPING_FIELDS = (
    "wpm",
    "errorRate",
    "backspaces",
    "avgInterval",
    "variance",
    "avgDwell",
    "burstLength",
    "pauseFrequency",
    "totalKeys",
    "errCorrectionRate",
)
MEMORY_FIELDS = ("accuracy", "responseTime", "distractionScore")
ATTENTION_FIELDS = ("accuracy", "avgRT", "errors", "congruentAcc", "incongruentAcc")
SURVEY_FIELDS = (
    "stress",
    "fatigue",
    "motivation",
    "mood",
    "sleep",
    "study",
    "homework",
    "exam",
    "socialStress",
    "physicalActivity",
)
NASA_TLX_FIELDS = (
    "mentalDemand",
    "physicalDemand",
    "temporalDemand",
    "performance",
    "effort",
    "frustration",
    "tlxScore",
)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _prefix_features(prefix: str, payload: dict[str, Any] | None, fields: tuple[str, ...]) -> dict[str, Any]:
    features: dict[str, Any] = {}
    for field in fields:
        key = f"{prefix}_{field}"
        if payload is None:
            features[key] = None
            continue
        raw = payload.get(field)
        if field == "exam":
            features[key] = _to_bool(raw)
        else:
            features[key] = _to_float(raw)
    return features


def _extract_reaction(payload: dict[str, Any] | None) -> dict[str, Any]:
    features = _prefix_features("reaction", payload, REACTION_FIELDS)
    if payload is not None:
        features["reaction_trials"] = _to_float(payload.get("trials"))
    else:
        features["reaction_trials"] = None
    return features


def _extract_gamification(game_data: dict[str, Any] | None) -> dict[str, Any]:
    if game_data is None:
        return {
            "gamification_coins": None,
            "gamification_streak": None,
            "gamification_level": None,
            "gamification_xp": None,
            "gamification_totalDays": None,
        }
    pet = game_data.get("pet") or {}
    return {
        "gamification_coins": _to_float(game_data.get("coins")),
        "gamification_streak": _to_float(game_data.get("streak")),
        "gamification_level": _to_float(pet.get("level")),
        "gamification_xp": _to_float(pet.get("xp")),
        "gamification_totalDays": _to_float(game_data.get("totalDays")),
    }


def _compute_derived_features(features: dict[str, Any], joined_at: datetime, session_date: date) -> dict[str, Any]:
    derived: dict[str, Any] = {}

    reaction_avg = features.get("reaction_avg")
    reaction_sd = features.get("reaction_sd")
    reaction_missed = features.get("reaction_missed")
    reaction_trials = features.get("reaction_trials")

    if reaction_avg and reaction_avg > 0 and reaction_sd is not None:
        derived["reaction_cv"] = round(reaction_sd / reaction_avg, 6)
    else:
        derived["reaction_cv"] = None

    if reaction_trials and reaction_trials > 0 and reaction_missed is not None:
        derived["reaction_lapse_rate"] = round(reaction_missed / reaction_trials, 6)
    else:
        derived["reaction_lapse_rate"] = None

    typing_variance = features.get("typing_variance")
    derived["typing_irregularity"] = typing_variance

    memory_accuracy = features.get("memory_accuracy")
    memory_response_time = features.get("memory_responseTime")
    if memory_accuracy is not None and memory_response_time and memory_response_time > 0:
        derived["memory_efficiency"] = round(memory_accuracy / memory_response_time, 6)
    else:
        derived["memory_efficiency"] = None

    congruent = features.get("attention_congruentAcc")
    incongruent = features.get("attention_incongruentAcc")
    if congruent is not None and incongruent is not None:
        derived["stroop_interference"] = round(congruent - incongruent, 6)
    else:
        derived["stroop_interference"] = None

    study = features.get("survey_study") or 0.0
    homework = features.get("survey_homework") or 0.0
    if features.get("survey_study") is not None or features.get("survey_homework") is not None:
        derived["study_load"] = round(study + homework, 6)
    else:
        derived["study_load"] = None

    joined_date = joined_at.date() if isinstance(joined_at, datetime) else joined_at
    derived["days_since_join"] = (session_date - joined_date).days

    return derived


def _compute_quality_flags(
    module_payloads: dict[str, dict[str, Any]],
    session_complete: bool,
    has_game_data: bool,
) -> dict[str, bool]:
    missing_reaction = "reaction" not in module_payloads
    missing_typing = "typing" not in module_payloads
    missing_memory = "memory" not in module_payloads
    missing_attention = "attention" not in module_payloads
    missing_survey = "survey" not in module_payloads
    missing_tlx = "nasaTLX" not in module_payloads
    missing_game = not has_game_data

    complete_day = session_complete
    valid_for_ml = (
        complete_day
        and not missing_reaction
        and not missing_typing
        and not missing_memory
        and not missing_attention
        and not missing_survey
    )

    return {
        "missing_reaction": missing_reaction,
        "missing_typing": missing_typing,
        "missing_memory": missing_memory,
        "missing_attention": missing_attention,
        "missing_survey": missing_survey,
        "missing_tlx": missing_tlx,
        "missing_game": missing_game,
        "complete_day": complete_day,
        "valid_for_ml": valid_for_ml,
        "gamification_is_snapshot": has_game_data,
    }


def build_participant_day_record(
    *,
    participant: Participant,
    session: DailySession,
    game_data: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, bool]]:
    module_payloads = {
        module_result.module_key: module_result.payload
        for module_result in session.module_results
    }

    features: dict[str, Any] = {
        "participant_public_id": participant.public_id,
        "session_date": session.session_date.isoformat(),
        "participant_grade": participant.grade,
        "participant_age_range": participant.age_range,
        "participant_joined_at": participant.created_at.isoformat(),
        "session_complete": session.complete,
    }

    features.update(_extract_reaction(module_payloads.get("reaction")))
    features.update(_prefix_features("typing", module_payloads.get("typing"), TYPING_FIELDS))
    features.update(_prefix_features("memory", module_payloads.get("memory"), MEMORY_FIELDS))
    features.update(_prefix_features("attention", module_payloads.get("attention"), ATTENTION_FIELDS))
    features.update(_prefix_features("survey", module_payloads.get("survey"), SURVEY_FIELDS))
    features.update(_prefix_features("nasa_tlx", module_payloads.get("nasaTLX"), NASA_TLX_FIELDS))
    features.update(_extract_gamification(game_data))
    features.update(_compute_derived_features(features, participant.created_at, session.session_date))

    quality_flags = _compute_quality_flags(
        module_payloads,
        session_complete=session.complete,
        has_game_data=game_data is not None,
    )

    return features, quality_flags


def _next_dataset_version(db: Session) -> int:
    current = db.execute(select(func.max(MLDataset.dataset_version))).scalar_one()
    return (current or 0) + 1


def _evaluate_session_dataset_eligibility(
    db: Session,
    *,
    participant: Participant,
    session: DailySession,
    dataset_mode: str,
) -> tuple[bool, list[str], list[str]]:
    exclusion_reasons: list[str] = []
    warning_labels: list[str] = []

    if is_synthetic_public_id(participant.public_id):
        exclusion_reasons.append("SYNTHETIC_TEST_DATA")
        return False, exclusion_reasons, warning_labels

    consent_ok, consent_reasons = consent_eligible_at_session_time(db, participant, session)
    if not consent_ok:
        exclusion_reasons.extend(consent_reasons)
        return False, exclusion_reasons, warning_labels

    if session.status != SESSION_STATUS_COMPLETE:
        exclusion_reasons.append("SESSION_NOT_COMPLETED")
        return False, exclusion_reasons, warning_labels

    procedure = resolve_active_procedure(db)
    required_modules = set(procedure.required_modules or [])
    present_modules = {result.module_key for result in session.module_results}
    if not required_modules.issubset(present_modules):
        exclusion_reasons.append("REQUIRED_MODULES_MISSING")
        return False, exclusion_reasons, warning_labels

    if session_has_reviewed_exclude(db, session.id):
        exclusion_reasons.append("REVIEWED_EXCLUDE")
        return False, exclusion_reasons, warning_labels

    unresolved_critical = session_has_unresolved_critical_flags(db, session.id)
    if unresolved_critical:
        if dataset_mode == "strict":
            exclusion_reasons.append("UNRESOLVED_CRITICAL_DATA_QUALITY_FLAG")
            return False, exclusion_reasons, warning_labels
        warning_labels.append("UNRESOLVED_CRITICAL_DATA_QUALITY_FLAG")

    if dataset_mode == "exploratory":
        for flag in session.data_quality_flags:
            if flag.review_status == "unresolved" and flag.severity == "non_critical":
                warning_labels.append(flag.flag_type)

    eligible = len(exclusion_reasons) == 0
    return eligible, exclusion_reasons, warning_labels


def build_research_dataset(
    db: Session,
    *,
    researcher_id: UUID | None = None,
    name: str | None = None,
    dataset_mode: str = "strict",
) -> MLDataset:
    if dataset_mode not in {"strict", "exploratory"}:
        raise ValueError("dataset_mode must be 'strict' or 'exploratory'")

    participants = db.execute(
        apply_participant_filter(
            select(Participant)
            .options(
                selectinload(Participant.daily_sessions)
                .selectinload(DailySession.module_results),
                selectinload(Participant.daily_sessions)
                .selectinload(DailySession.data_quality_flags),
                selectinload(Participant.game_data),
            )
            .order_by(Participant.created_at.asc())
        )
    ).scalars().all()

    version = _next_dataset_version(db)
    mode_suffix = "strict" if dataset_mode == "strict" else "exploratory"
    build_name = name or f"research-dataset-{mode_suffix}-v{version}"
    now = datetime.now(timezone.utc)

    dataset = MLDataset(
        name=build_name,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        dataset_version=version,
        row_count=0,
        participant_count=0,
        created_by_researcher_id=researcher_id,
        dataset_mode=dataset_mode,
    )
    db.add(dataset)
    db.flush()

    row_models: list[MLDatasetRow] = []
    participant_ids: set[UUID] = set()
    session_dates: list[date] = []

    for participant in participants:
        game_payload = participant.game_data.game_data if participant.game_data else None
        for session in sorted(
            participant.daily_sessions,
            key=lambda item: (item.session_date, item.session_slot),
        ):
            eligible, exclusion_reasons, warning_labels = _evaluate_session_dataset_eligibility(
                db,
                participant=participant,
                session=session,
                dataset_mode=dataset_mode,
            )
            if not eligible:
                continue

            features, quality_flags = build_participant_day_record(
                participant=participant,
                session=session,
                game_data=game_payload,
            )
            if warning_labels:
                quality_flags = {
                    **quality_flags,
                    "exploratory_warning_labels": warning_labels,
                    "dataset_mode": dataset_mode,
                }
            else:
                quality_flags = {**quality_flags, "dataset_mode": dataset_mode}

            row_models.append(
                MLDatasetRow(
                    dataset_id=dataset.id,
                    participant_id=participant.id,
                    public_id=participant.public_id,
                    session_date=session.session_date,
                    session_id=session.id,
                    features=features,
                    quality_flags=quality_flags,
                    exclusion_reasons=exclusion_reasons or None,
                    labels={},
                )
            )
            participant_ids.add(participant.id)
            session_dates.append(session.session_date)

    if row_models:
        db.add_all(row_models)

    dataset.row_count = len(row_models)
    dataset.participant_count = len(participant_ids)
    dataset.date_range_start = min(session_dates) if session_dates else None
    dataset.date_range_end = max(session_dates) if session_dates else None
    dataset.created_at = now

    db.commit()
    db.refresh(dataset)
    return dataset


def summarize_dataset(db: Session, dataset_id: UUID) -> dict[str, Any]:
    dataset = db.get(MLDataset, dataset_id)
    if dataset is None:
        raise ValueError("Dataset not found")

    rows = db.execute(
        select(MLDatasetRow).where(MLDatasetRow.dataset_id == dataset_id)
    ).scalars().all()

    def flag_count(flag_name: str) -> int:
        return sum(1 for row in rows if row.quality_flags.get(flag_name))

    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "feature_schema_version": dataset.feature_schema_version,
        "dataset_version": dataset.dataset_version,
        "row_count": dataset.row_count,
        "participant_count": dataset.participant_count,
        "date_range_start": dataset.date_range_start,
        "date_range_end": dataset.date_range_end,
        "complete_day_count": flag_count("complete_day"),
        "valid_for_ml_count": flag_count("valid_for_ml"),
        "missing_reaction_count": flag_count("missing_reaction"),
        "missing_typing_count": flag_count("missing_typing"),
        "missing_memory_count": flag_count("missing_memory"),
        "missing_attention_count": flag_count("missing_attention"),
        "missing_survey_count": flag_count("missing_survey"),
        "missing_tlx_count": flag_count("missing_tlx"),
        "missing_game_count": flag_count("missing_game"),
        "gamification_snapshot_rows": sum(
            1 for row in rows if row.quality_flags.get("gamification_is_snapshot")
        ),
    }
