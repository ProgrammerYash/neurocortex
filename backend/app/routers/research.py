from uuid import UUID

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_researcher
from app.models.ml_dataset import MLDataset
from app.models.researcher import Researcher
from app.schemas.ml import (
    BuildDatasetRequest,
    DatasetCorrelationsResponse,
    DatasetLabelsResponse,
    DatasetMetadata,
    DatasetQualityResponse,
    DatasetRow,
    DatasetRowPage,
    DatasetStatisticsResponse,
    DatasetSummary,
    LabelGenerationResponse,
)
from app.schemas.consent import (
    ConsentStatusResponse,
    ResearcherConsentEventRequest,
    ResolveAgeConsentCategoryRequest,
)
from app.schemas.research import ResearchParticipantRecord, ResearchStatsResponse
from app.schemas.session import DailySessionRecord
from app.schemas.procedure import (
    DataQualityDashboardResponse,
    FlaggedSessionRecord,
    ReviewDataQualityFlagRequest,
    StudyProcedureResponse,
)
from app.services.data_quality_service import (
    DataQualityError,
    build_data_quality_dashboard,
    list_flagged_sessions,
    review_data_quality_flag,
    serialize_flag,
)
from app.services.procedure_service import get_active_procedure_for_researcher
from app.schemas.study import StudyConfigResponse
from app.services.ml_dataset_service import (
    DatasetError,
    create_dataset,
    get_dataset,
    get_dataset_correlations,
    get_dataset_labels,
    get_dataset_quality,
    get_dataset_statistics,
    get_dataset_summary,
    label_dataset,
    list_dataset_rows,
    list_datasets,
)
from app.schemas.ml_model import MLModelDetail, MLModelSummary, TrainModelRequest, TrainModelResponse
from app.schemas.ml_prediction import (
    BatchPredictResponse,
    PredictRequest,
    PredictResponse,
    PredictionRecord,
)
from app.schemas.ml_explanation import (
    ExplainResponse,
    ModelComparisonItem,
    ModelFeatureImportanceResponse,
)
from app.services.ml_explainability import (
    ExplainabilityError,
    compare_models,
    generate_explanation,
    get_explanation,
    get_model_feature_importance,
)
from app.services.ml_inference import (
    InferenceError,
    batch_predict,
    get_participant_predictions,
    list_predictions,
    predict_participant_session,
    risk_level,
)
from app.services.ml_training import TrainingError, get_model, list_models, train_model
from app.services.research_service import (
    get_research_stats,
    list_research_participants,
    list_research_sessions,
)
from app.services.consent_service import (
    ConsentError,
    build_consent_status,
    get_participant_by_public_id,
    list_enrollment_statuses,
    record_researcher_consent_event,
    resolve_participant_age_consent_category,
    set_ml_exclusion,
)
from app.services.study_guard import get_study_config

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/study-procedure", response_model=StudyProcedureResponse)
def get_active_study_procedure(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> StudyProcedureResponse:
    return StudyProcedureResponse(**get_active_procedure_for_researcher(db))


@router.get("/data-quality/dashboard", response_model=DataQualityDashboardResponse)
def get_data_quality_dashboard(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DataQualityDashboardResponse:
    return DataQualityDashboardResponse(**build_data_quality_dashboard(db))


@router.get("/data-quality/flagged-sessions", response_model=list[FlaggedSessionRecord])
def get_flagged_sessions(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[FlaggedSessionRecord]:
    return [FlaggedSessionRecord(**item) for item in list_flagged_sessions(db)]


@router.post("/data-quality/flags/{flag_id}/review")
def review_flag(
    flag_id: UUID,
    payload: ReviewDataQualityFlagRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> dict:
    try:
        flag = review_data_quality_flag(
            db,
            flag_id=flag_id,
            researcher_id=researcher.id,
            review_status=payload.review_status,
        )
    except DataQualityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return serialize_flag(flag)


@router.get("/study-config", response_model=StudyConfigResponse)
def get_research_study_config(
    _researcher: Researcher = Depends(get_current_researcher),
) -> StudyConfigResponse:
    return StudyConfigResponse(**get_study_config())


@router.get("/enrollment-status", response_model=list[ConsentStatusResponse])
def get_enrollment_status(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[ConsentStatusResponse]:
    return list_enrollment_statuses(db)


@router.get("/participants/{public_id}/consent-status", response_model=ConsentStatusResponse)
def get_participant_consent_status(
    public_id: str,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        participant = get_participant_by_public_id(db, public_id)
        return build_consent_status(db, participant)
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "error_code": exc.error_code}) from exc


@router.post("/participants/{public_id}/consent-event", response_model=ConsentStatusResponse)
def post_participant_consent_event(
    public_id: str,
    payload: ResearcherConsentEventRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        participant = get_participant_by_public_id(db, public_id)
        return record_researcher_consent_event(
            db,
            participant=participant,
            researcher_id=researcher.id,
            payload=payload.model_dump(),
        )
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "error_code": exc.error_code}) from exc


@router.post("/participants/{public_id}/resolve-age-category", response_model=ConsentStatusResponse)
def resolve_participant_age_category(
    public_id: str,
    payload: ResolveAgeConsentCategoryRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        participant = get_participant_by_public_id(db, public_id)
        return resolve_participant_age_consent_category(
            db,
            participant=participant,
            researcher_id=researcher.id,
            age_consent_category=payload.age_consent_category,
        )
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "error_code": exc.error_code}) from exc


@router.post("/participants/{public_id}/exclude-from-ml", response_model=ConsentStatusResponse)
def exclude_participant_from_ml(
    public_id: str,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        participant = get_participant_by_public_id(db, public_id)
        return set_ml_exclusion(db, participant=participant, researcher_id=researcher.id, excluded=True)
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "error_code": exc.error_code}) from exc


@router.post("/participants/{public_id}/include-in-ml", response_model=ConsentStatusResponse)
def include_participant_in_ml(
    public_id: str,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    try:
        participant = get_participant_by_public_id(db, public_id)
        return set_ml_exclusion(db, participant=participant, researcher_id=researcher.id, excluded=False)
    except ConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "error_code": exc.error_code}) from exc


@router.get("/participants", response_model=list[ResearchParticipantRecord])
def get_research_participants(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_research_participants(db)


@router.get("/sessions", response_model=list[DailySessionRecord])
def get_research_sessions(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_research_sessions(db)


@router.get("/stats", response_model=ResearchStatsResponse)
def get_research_stats_endpoint(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ResearchStatsResponse:
    return get_research_stats(db)


@router.post("/datasets/build", response_model=DatasetMetadata, status_code=status.HTTP_201_CREATED)
def build_research_dataset_endpoint(
    payload: BuildDatasetRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> MLDataset:
    try:
        return create_dataset(
            db,
            researcher_id=researcher.id,
            name=payload.name,
            dataset_mode=payload.dataset_mode,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to build research dataset",
        ) from exc


@router.get("/datasets", response_model=list[DatasetMetadata])
def get_research_datasets(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[MLDataset]:
    return list_datasets(db)


@router.get("/datasets/{dataset_id}", response_model=DatasetMetadata)
def get_research_dataset(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> MLDataset:
    try:
        return get_dataset(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/datasets/{dataset_id}/summary", response_model=DatasetSummary)
def get_research_dataset_summary(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DatasetSummary:
    try:
        return get_dataset_summary(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/datasets/{dataset_id}/rows", response_model=DatasetRowPage)
def get_research_dataset_rows(
    dataset_id: UUID,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DatasetRowPage:
    try:
        rows, total = list_dataset_rows(db, dataset_id, limit=limit, offset=offset)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DatasetRowPage(items=rows, total=total, limit=limit, offset=offset)


@router.post("/datasets/{dataset_id}/label", response_model=LabelGenerationResponse)
def label_research_dataset(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> LabelGenerationResponse:
    try:
        result = label_dataset(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return LabelGenerationResponse(
        dataset_id=UUID(result["dataset_id"]),
        dataset_version=result["dataset_version"],
        feature_schema_version=result["feature_schema_version"],
        label_schema_version=result["label_schema_version"],
        generated_at=datetime.fromisoformat(result["generated_at"]),
        row_count=result["row_count"],
        labeled_rows=result["labeled_rows"],
        burnout_next_day_labeled=result["burnout_next_day_labeled"],
        burnout_next_day_true=result["burnout_next_day_true"],
        burnout_next_day_false=result["burnout_next_day_false"],
        burnout_prevalence=result["burnout_prevalence"],
        high_workload_next_day_true=result["high_workload_next_day_true"],
        study_dropout_true=result["study_dropout_true"],
        valid_training_rows=result["valid_training_rows"],
    )


@router.get("/datasets/{dataset_id}/statistics", response_model=DatasetStatisticsResponse)
def get_research_dataset_statistics(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DatasetStatisticsResponse:
    try:
        return get_dataset_statistics(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/datasets/{dataset_id}/correlations", response_model=DatasetCorrelationsResponse)
def get_research_dataset_correlations(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DatasetCorrelationsResponse:
    try:
        return get_dataset_correlations(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/datasets/{dataset_id}/quality", response_model=DatasetQualityResponse)
def get_research_dataset_quality(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DatasetQualityResponse:
    try:
        return get_dataset_quality(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/datasets/{dataset_id}/labels", response_model=DatasetLabelsResponse)
def get_research_dataset_labels(
    dataset_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DatasetLabelsResponse:
    try:
        return get_dataset_labels(db, dataset_id)
    except DatasetError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/models/train", response_model=TrainModelResponse, status_code=status.HTTP_201_CREATED)
def train_research_model(
    payload: TrainModelRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> TrainModelResponse:
    try:
        model = train_model(
            db,
            dataset_id=payload.dataset_id,
            target_label=payload.target_label,
            model_type=payload.model_type,
            researcher_id=researcher.id,
        )
    except TrainingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to train model",
        ) from exc
    return TrainModelResponse(
        model_id=model.id,
        status="completed",
        metrics=model.metrics,
    )


@router.get("/models/compare", response_model=list[ModelComparisonItem])
def compare_research_models(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[ModelComparisonItem]:
    return compare_models(db)


@router.get("/models", response_model=list[MLModelSummary])
def get_research_models(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list:
    return list_models(db)


@router.get("/models/{model_id}", response_model=MLModelDetail)
def get_research_model(
    model_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> MLModelDetail:
    try:
        return get_model(db, model_id)
    except TrainingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get("/models/{model_id}/feature-importance", response_model=ModelFeatureImportanceResponse)
def get_research_model_feature_importance(
    model_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ModelFeatureImportanceResponse:
    try:
        return get_model_feature_importance(db, model_id=model_id)
    except ExplainabilityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/models/{model_id}/predict", response_model=PredictResponse, status_code=status.HTTP_201_CREATED)
def predict_research_model(
    model_id: UUID,
    payload: PredictRequest,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> PredictResponse:
    try:
        record = predict_participant_session(
            db,
            model_id=model_id,
            participant_id=payload.participant_id,
            session_date=payload.session_date,
        )
    except InferenceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return PredictResponse(
        prediction_id=record.id,
        probability=record.probability,
        prediction=record.prediction,
        risk_level=risk_level(record.probability),
        confidence=record.confidence,
    )


@router.post("/models/{model_id}/batch-predict", response_model=BatchPredictResponse)
def batch_predict_research_model(
    model_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> BatchPredictResponse:
    try:
        result = batch_predict(db, model_id=model_id)
    except InferenceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return BatchPredictResponse(**result)


@router.get("/predictions", response_model=list[PredictionRecord])
def get_research_predictions(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[PredictionRecord]:
    return list_predictions(db)


@router.get("/predictions/{participant_id}", response_model=list[PredictionRecord])
def get_research_participant_predictions(
    participant_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[PredictionRecord]:
    try:
        return get_participant_predictions(db, participant_id)
    except InferenceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/predictions/{prediction_id}/explain", response_model=ExplainResponse, status_code=status.HTTP_201_CREATED)
def explain_research_prediction(
    prediction_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ExplainResponse:
    try:
        record = generate_explanation(db, prediction_id=prediction_id)
    except ExplainabilityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return ExplainResponse(prediction_id=prediction_id, explanation=record.explanation)


@router.get("/predictions/{prediction_id}/explanation", response_model=ExplainResponse)
def get_research_prediction_explanation(
    prediction_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ExplainResponse:
    try:
        record = get_explanation(db, prediction_id=prediction_id)
    except ExplainabilityError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return ExplainResponse(prediction_id=prediction_id, explanation=record.explanation)
