import csv
import io
import os
import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_golden_vault
from app.schemas.golden_vault import (
    GoldenVaultAmountRequest,
    GoldenVaultAuditItem,
    GoldenVaultAutoDataPatchRequest,
    GoldenVaultAutoDataPreviewResponse,
    GoldenVaultAutoDataRequest,
    GoldenVaultAutoSessionPatchRequest,
    GoldenVaultAutoSessionResponse,
    GoldenVaultBulkRequest,
    GoldenVaultBulkResult,
    GoldenVaultCoinAdjustRequest,
    GoldenVaultFakeUsersBatchResponse,
    GoldenVaultFakeUsersCredentialsResponse,
    GoldenVaultFakeUsersGenerateRequest,
    GoldenVaultFakeUsersPreviewRequest,
    GoldenVaultFakeUsersPreviewResponse,
    GoldenVaultFakeUsersProcessResponse,
    GoldenVaultLoginRequest,
    GoldenVaultLoginResponse,
    GoldenVaultParticipantListResponse,
    GoldenVaultParticipantRow,
    GoldenVaultPatchRequest,
    GoldenVaultSessionAdjustRequest,
)
from app.services.golden_vault_auth_service import GoldenVaultAuthError, login_golden_vault
from app.services.golden_vault_service import (
    GoldenVaultError,
    add_bonus_coins,
    add_bonus_sessions,
    adjust_coins,
    adjust_sessions,
    apply_auto_data_backfill_continue,
    apply_auto_data_for_public_id,
    build_demo_dashboard_export_rows,
    delete_bonus_coins,
    delete_bonus_sessions,
    disable_override,
    enable_override,
    get_vault_participant,
    list_recent_audit_events,
    list_vault_participants,
    patch_auto_data_schedule,
    patch_override,
    preview_auto_data_for_public_id,
    regenerate_demo_feedback,
    regenerate_metrics,
    release_demo_feedback,
    reset_all_demo,
    revoke_demo_feedback,
    run_bulk_action,
    reschedule_auto_session_for_public_id,
    run_auto_session_now_for_public_id,
    set_auto_session_enabled,
)
from app.services.golden_vault_auto_session_service import process_due_golden_auto_sessions
from app.services.golden_vault_fake_user_service import (
    FakeUserBatchError,
    batch_status_payload,
    claim_batch_credentials,
    create_fake_user_batch,
    preview_fake_users,
    process_fake_user_batch_chunk,
)

router = APIRouter(prefix="/golden-vault", tags=["golden-vault"])


def _persist(db: Session) -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        db.flush()
    else:
        db.commit()


def _rollback(db: Session) -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        db.rollback()
    else:
        db.rollback()


@router.post("/login", response_model=GoldenVaultLoginResponse)
def golden_vault_login(
    payload: GoldenVaultLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> GoldenVaultLoginResponse:
    try:
        data = login_golden_vault(db, code=payload.code, request=request)
        _persist(db)
        return GoldenVaultLoginResponse(**data)
    except GoldenVaultAuthError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc


@router.get("/participants", response_model=GoldenVaultParticipantListResponse)
def golden_vault_list_participants(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    golden_enabled: str | None = None,
    feedback_filter: str | None = None,
    synthetic_batch_id: str | None = None,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultParticipantListResponse:
    items, total = list_vault_participants(
        db,
        limit=limit,
        offset=offset,
        search=search,
        golden_enabled=golden_enabled,
        feedback_filter=feedback_filter,
        synthetic_batch_id=synthetic_batch_id,
    )
    return GoldenVaultParticipantListResponse(
        items=[GoldenVaultParticipantRow(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/participants/{public_id}", response_model=GoldenVaultParticipantRow)
def golden_vault_get_participant(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultParticipantRow:
    row = get_vault_participant(db, public_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Participant not found"})
    return GoldenVaultParticipantRow(**row)


@router.patch("/participants/{public_id}", response_model=GoldenVaultParticipantRow)
def golden_vault_patch_participant(
    public_id: str,
    payload: GoldenVaultPatchRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultParticipantRow:
    try:
        patch_override(db, public_id=public_id, payload=payload.model_dump(exclude_unset=True))
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    row = get_vault_participant(db, public_id)
    return GoldenVaultParticipantRow(**row)


@router.post("/participants/{public_id}/sessions")
def golden_vault_adjust_sessions(
    public_id: str,
    payload: GoldenVaultSessionAdjustRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    if payload.delta is None and payload.set_to is None:
        raise HTTPException(status_code=422, detail={"message": "Provide delta or set_to"})
    try:
        adjust_sessions(db, public_id=public_id, delta=payload.delta, set_to=payload.set_to)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/coins")
def golden_vault_adjust_coins(
    public_id: str,
    payload: GoldenVaultCoinAdjustRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    if payload.delta is None and payload.set_to is None:
        raise HTTPException(status_code=422, detail={"message": "Provide delta or set_to"})
    try:
        adjust_coins(db, public_id=public_id, delta=payload.delta, set_to=payload.set_to)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/sessions/add")
def golden_vault_add_sessions(
    public_id: str,
    payload: GoldenVaultAmountRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        add_bonus_sessions(db, public_id=public_id, amount=payload.amount)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/sessions/delete")
def golden_vault_delete_sessions(
    public_id: str,
    payload: GoldenVaultAmountRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        delete_bonus_sessions(db, public_id=public_id, amount=payload.amount)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/coins/add")
def golden_vault_add_coins(
    public_id: str,
    payload: GoldenVaultAmountRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        add_bonus_coins(db, public_id=public_id, amount=payload.amount)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/coins/delete")
def golden_vault_delete_coins(
    public_id: str,
    payload: GoldenVaultAmountRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        delete_bonus_coins(db, public_id=public_id, amount=payload.amount)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/auto-data/preview", response_model=GoldenVaultAutoDataPreviewResponse)
def golden_vault_auto_data_preview(
    public_id: str,
    payload: GoldenVaultAutoDataRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultAutoDataPreviewResponse:
    try:
        preview = preview_auto_data_for_public_id(db, public_id=public_id, payload=payload.model_dump())
        _persist(db)
    except (GoldenVaultError, ValueError) as exc:
        _rollback(db)
        message = exc.message if isinstance(exc, GoldenVaultError) else str(exc)
        status = exc.status_code if isinstance(exc, GoldenVaultError) else 422
        raise HTTPException(status_code=status, detail={"message": message}) from exc
    return GoldenVaultAutoDataPreviewResponse(**preview)


@router.patch("/participants/{public_id}/auto-data")
def golden_vault_patch_auto_data(
    public_id: str,
    payload: GoldenVaultAutoDataPatchRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        patch_auto_data_schedule(db, public_id=public_id, payload=payload.model_dump(exclude_unset=True))
        _persist(db)
    except (GoldenVaultError, ValueError) as exc:
        _rollback(db)
        message = exc.message if isinstance(exc, GoldenVaultError) else str(exc)
        status = exc.status_code if isinstance(exc, GoldenVaultError) else 422
        raise HTTPException(status_code=status, detail={"message": message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/auto-data/apply")
def golden_vault_apply_auto_data(
    public_id: str,
    payload: GoldenVaultAutoDataRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        result = apply_auto_data_for_public_id(db, public_id=public_id, payload=payload.model_dump())
        while result.get("backfill", {}).get("remaining", 0) > 0:
            cont = apply_auto_data_backfill_continue(db, public_id=public_id)
            result["backfill"]["created"] = result["backfill"].get("created", 0) + cont.get("created", 0)
            result["backfill"]["remaining"] = cont.get("remaining", 0)
            if cont.get("created", 0) == 0:
                break
        _persist(db)
    except (GoldenVaultError, ValueError) as exc:
        _rollback(db)
        message = exc.message if isinstance(exc, GoldenVaultError) else str(exc)
        status = exc.status_code if isinstance(exc, GoldenVaultError) else 422
        raise HTTPException(status_code=status, detail={"message": message}) from exc
    row = get_vault_participant(db, public_id)
    return {"participant": row, "backfill": result.get("backfill")}


@router.post("/participants/auto-data/bulk/preview")
def golden_vault_bulk_auto_data_preview(
    payload: GoldenVaultAutoDataRequest,
    participant_public_ids: list[str] = Query(default=[]),
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    previews = []
    for public_id in participant_public_ids:
        try:
            previews.append(
                {
                    "participantId": public_id,
                    "preview": preview_auto_data_for_public_id(db, public_id=public_id, payload=payload.model_dump()),
                }
            )
        except Exception as exc:
            previews.append({"participantId": public_id, "error": str(exc)})
    _persist(db)
    return {"items": previews}


@router.post("/participants/auto-data/bulk")
def golden_vault_bulk_auto_data(
    payload: GoldenVaultBulkRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    config = payload.filters.get("auto_data") if payload.filters else None
    if not config:
        raise HTTPException(status_code=422, detail={"message": "auto_data config required in filters"})
    ids = payload.participant_public_ids or []
    succeeded = failed = skipped = 0
    failures: list[dict[str, str]] = []
    for public_id in ids:
        try:
            apply_auto_data_for_public_id(db, public_id=public_id, payload=config)
            succeeded += 1
        except GoldenVaultError as exc:
            if exc.status_code == 404:
                skipped += 1
            else:
                failed += 1
                failures.append({"participantId": public_id, "message": exc.message})
        except Exception as exc:
            failed += 1
            failures.append({"participantId": public_id, "message": str(exc)})
    _persist(db)
    return GoldenVaultBulkResult(
        requested_count=len(ids),
        succeeded_count=succeeded,
        failed_count=failed,
        skipped_count=skipped,
        failures=failures,
    )


@router.post("/participants/{public_id}/regenerate-metrics")
def golden_vault_regenerate_metrics(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        regenerate_metrics(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/feedback/release")
def golden_vault_release_feedback(public_id: str, _vault: dict = Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    try:
        release_demo_feedback(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/feedback/revoke")
def golden_vault_revoke_feedback(public_id: str, _vault: dict = Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    try:
        revoke_demo_feedback(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/feedback/regenerate")
def golden_vault_regenerate_feedback(public_id: str, _vault: dict = Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    try:
        regenerate_demo_feedback(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


@router.post("/participants/{public_id}/reset")
def golden_vault_reset_participant(public_id: str, _vault: dict = Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    try:
        reset_all_demo(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return get_vault_participant(db, public_id)


def _auto_session_response(db: Session, public_id: str) -> GoldenVaultAutoSessionResponse:
    row = get_vault_participant(db, public_id)
    if row is None:
        raise HTTPException(status_code=404, detail={"message": "Participant not found"})
    return GoldenVaultAutoSessionResponse(
        publicId=row["participantId"],
        autoSessionEnabled=bool(row.get("autoSessionEnabled")),
        nextAutoSessionAt=row.get("nextAutoSessionAt"),
        lastAutoSessionAt=row.get("lastAutoSessionAt"),
        bonusSessions=int(row.get("bonusSessions") or 0),
        displayedCompletedSessions=int(row.get("displayedCompletedSessions") or 0),
    )


@router.patch("/participants/{public_id}/auto-session", response_model=GoldenVaultAutoSessionResponse)
def golden_vault_patch_auto_session(
    public_id: str,
    payload: GoldenVaultAutoSessionPatchRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultAutoSessionResponse:
    try:
        set_auto_session_enabled(db, public_id=public_id, enabled=payload.enabled)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return _auto_session_response(db, public_id)


@router.post("/participants/{public_id}/auto-session/reschedule", response_model=GoldenVaultAutoSessionResponse)
def golden_vault_reschedule_auto_session(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultAutoSessionResponse:
    try:
        reschedule_auto_session_for_public_id(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    except ValueError as exc:
        _rollback(db)
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc
    return _auto_session_response(db, public_id)


@router.post("/participants/{public_id}/auto-session/run-now", response_model=GoldenVaultAutoSessionResponse)
def golden_vault_run_auto_session_now(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultAutoSessionResponse:
    try:
        run_auto_session_now_for_public_id(db, public_id=public_id)
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return _auto_session_response(db, public_id)


@router.post("/participants/auto-session/bulk", response_model=GoldenVaultBulkResult)
def golden_vault_auto_session_bulk(
    payload: GoldenVaultBulkRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultBulkResult:
    try:
        result = run_bulk_action(db, payload=payload.model_dump())
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return GoldenVaultBulkResult(**result)


@router.post("/auto-sessions/process-due")
def golden_vault_process_due_auto_sessions(
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    summary = process_due_golden_auto_sessions(db)
    _persist(db)
    return summary


@router.post("/participants/bulk", response_model=GoldenVaultBulkResult)
def golden_vault_bulk(
    payload: GoldenVaultBulkRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultBulkResult:
    try:
        result = run_bulk_action(db, payload=payload.model_dump())
        _persist(db)
    except GoldenVaultError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return GoldenVaultBulkResult(**result)


@router.get("/audit-history", response_model=list[GoldenVaultAuditItem])
def golden_vault_audit_history(
    limit: int = Query(50, ge=1, le=200),
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> list[GoldenVaultAuditItem]:
    items = list_recent_audit_events(db, limit=limit)
    return [GoldenVaultAuditItem(**item) for item in items]


def _parse_iso_date(value: str) -> date_type:
    try:
        return date_type.fromisoformat(value.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": "Invalid start_date"}) from exc


def _fake_user_distribution(payload: GoldenVaultFakeUsersPreviewRequest) -> tuple[int, date_type, int, int, int, int]:
    start = _parse_iso_date(payload.start_date)
    return (
        payload.total,
        start,
        payload.daily,
        payload.weekly,
        payload.two_days,
        payload.four_days,
    )


@router.post("/fake-users/preview", response_model=GoldenVaultFakeUsersPreviewResponse)
def golden_vault_fake_users_preview(
    payload: GoldenVaultFakeUsersPreviewRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultFakeUsersPreviewResponse:
    total, start, daily, weekly, two_days, four_days = _fake_user_distribution(payload)
    try:
        data = preview_fake_users(
            db,
            total=total,
            start_date=start,
            daily=daily,
            weekly=weekly,
            two_days=two_days,
            four_days=four_days,
        )
    except FakeUserBatchError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return GoldenVaultFakeUsersPreviewResponse(**data)


@router.post("/fake-users/generate", response_model=GoldenVaultFakeUsersBatchResponse)
def golden_vault_fake_users_generate(
    payload: GoldenVaultFakeUsersGenerateRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultFakeUsersBatchResponse:
    total, start, daily, weekly, two_days, four_days = _fake_user_distribution(payload)
    try:
        batch = create_fake_user_batch(
            db,
            total=total,
            start_date=start,
            daily=daily,
            weekly=weekly,
            two_days=two_days,
            four_days=four_days,
            idempotency_key=payload.idempotency_key,
        )
        _persist(db)
    except FakeUserBatchError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return GoldenVaultFakeUsersBatchResponse(**batch_status_payload(batch))


@router.get("/fake-users/batches/{batch_id}", response_model=GoldenVaultFakeUsersBatchResponse)
def golden_vault_fake_users_batch_status(
    batch_id: uuid.UUID,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultFakeUsersBatchResponse:
    from app.models.golden_fake_user_batch import GoldenFakeUserBatch

    batch = db.get(GoldenFakeUserBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail={"message": "Batch not found"})
    return GoldenVaultFakeUsersBatchResponse(**batch_status_payload(batch))


@router.post("/fake-users/batches/{batch_id}/process", response_model=GoldenVaultFakeUsersProcessResponse)
def golden_vault_fake_users_process_batch(
    batch_id: uuid.UUID,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultFakeUsersProcessResponse:
    try:
        result = process_fake_user_batch_chunk(db, batch_id=batch_id)
        _persist(db)
    except FakeUserBatchError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return GoldenVaultFakeUsersProcessResponse(**result)


@router.get("/fake-users/batches/{batch_id}/credentials", response_model=GoldenVaultFakeUsersCredentialsResponse)
def golden_vault_fake_users_batch_credentials(
    batch_id: uuid.UUID,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> GoldenVaultFakeUsersCredentialsResponse:
    try:
        payload = claim_batch_credentials(db, batch_id=batch_id)
        _persist(db)
    except FakeUserBatchError as exc:
        _rollback(db)
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message}) from exc
    return GoldenVaultFakeUsersCredentialsResponse(**payload)


@router.get("/export/demo-dashboard")
def golden_vault_export_demo_dashboard(
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    rows = build_demo_dashboard_export_rows(db)
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        buffer.write("participant_id,is_simulated\n")
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="demo-dashboard-export.csv"'},
    )
