import csv
import io
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_golden_vault
from app.schemas.golden_vault import (
    GoldenVaultAmountRequest,
    GoldenVaultAuditItem,
    GoldenVaultAutoSessionPatchRequest,
    GoldenVaultAutoSessionResponse,
    GoldenVaultBulkRequest,
    GoldenVaultBulkResult,
    GoldenVaultCoinAdjustRequest,
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
    adjust_coins,
    adjust_sessions,
    build_demo_dashboard_export_rows,
    disable_override,
    enable_override,
    get_vault_participant,
    list_recent_audit_events,
    list_vault_participants,
    patch_override,
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
