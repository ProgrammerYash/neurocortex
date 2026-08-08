"""Golden Vault proxy routes for full researcher participant management."""

from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_golden_vault
from app.models.participant import Participant
from app.models.researcher import Researcher
from app.schemas.account import (
    AccountActionListResponse,
    AccountActionRecord,
    AccountActionResponse,
    AccountReasonRequest,
    RemoveAccountRequest,
    SuspendParticipantRequest,
)
from app.schemas.bulk import (
    BulkActionResult,
    BulkEmailRequest,
    BulkMessageRequest,
    BulkReactivateRequest,
    BulkRemoveRequest,
    BulkSelectionRequest,
    BulkSuspendRequest,
)
from app.schemas.consent import ResearcherConsentPage
from app.schemas.message import MessagePage, MessageResponse, SendMessageRequest
from app.schemas.research import (
    DashboardParticipantDetail,
    DashboardParticipantsPage,
    DashboardSummaryResponse,
)
from app.services.consent_pdf_service import ConsentPdfError
from app.services.golden_vault_actor import get_golden_vault_actor_researcher
from app.services.legacy_consent_signature_service import delivery_bytes_for_record
from app.services.participant_account_service import (
    AccountError,
    disable_participant,
    enable_participant,
    list_account_actions,
    remove_participant_access,
    reset_participant_pin,
    suspend_participant,
    unsuspend_participant,
)
from app.services.participant_bulk_service import (
    BulkActionError,
    bulk_email,
    bulk_message,
    bulk_reactivate,
    bulk_refresh_feedback,
    bulk_release_feedback,
    bulk_remove,
    bulk_revoke_feedback,
    bulk_suspend,
)
from app.services.participant_message_service import MessageError, list_researcher_participant_messages, send_participant_message
from app.services.researcher_consent_service import ResearcherConsentError, get_consent, list_consents, safe_participant_filename
from app.services.researcher_dashboard_service import (
    get_dashboard_participant_detail,
    get_dashboard_summary,
    list_dashboard_participants,
)
from app.services.consent_service import ConsentError, get_participant_by_public_id
from app.services.participant_feedback_service import (
    ParticipantFeedbackError,
    refresh_participant_feedback,
    release_participant_feedback,
    revoke_participant_feedback,
)

router = APIRouter(prefix="/golden-vault/management", tags=["golden-vault-management"])


def _persist(db: Session) -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        db.flush()
    else:
        db.commit()


def _actor(db: Session) -> Researcher:
    return get_golden_vault_actor_researcher(db)


def _account_http_error(exc: AccountError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def _message_http_error(exc: MessageError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def gv_dashboard_summary(
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(**get_dashboard_summary(db))


@router.get("/dashboard/participants", response_model=DashboardParticipantsPage)
def gv_dashboard_participants(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    sort: str = Query(default="joined"),
    direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    status: str | None = Query(default=None, alias="status"),
    participant_type: str = Query(default="all", pattern="^(all|real|synthetic_demo)$"),
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> DashboardParticipantsPage:
    items, total = list_dashboard_participants(
        db,
        limit=limit,
        offset=offset,
        search=search,
        sort=sort,
        direction=direction,
        status_filter=status or "all_current",
        participant_type_filter=participant_type,
        include_participant_type=True,
    )
    return DashboardParticipantsPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/dashboard/participants/{public_id}", response_model=DashboardParticipantDetail)
def gv_dashboard_participant_detail(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> DashboardParticipantDetail:
    detail = get_dashboard_participant_detail(db, public_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    return DashboardParticipantDetail(**detail)


@router.post("/dashboard/participants/{public_id}/suspend", response_model=AccountActionResponse)
def gv_suspend(
    public_id: str,
    payload: SuspendParticipantRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionResponse:
    try:
        result = suspend_participant(
            db,
            public_id=public_id,
            researcher=_actor(db),
            duration=payload.duration,
            reason=payload.reason,
        )
        return AccountActionResponse(**result)
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.post("/dashboard/participants/{public_id}/unsuspend", response_model=AccountActionResponse)
def gv_unsuspend(
    public_id: str,
    payload: AccountReasonRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionResponse:
    try:
        return AccountActionResponse(
            **unsuspend_participant(db, public_id=public_id, researcher=_actor(db), reason=payload.reason)
        )
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.post("/dashboard/participants/{public_id}/reset-pin", response_model=AccountActionResponse)
def gv_reset_pin(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionResponse:
    try:
        return AccountActionResponse(**reset_participant_pin(db, public_id=public_id, researcher=_actor(db)))
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.post("/dashboard/participants/{public_id}/disable", response_model=AccountActionResponse)
def gv_disable(
    public_id: str,
    payload: AccountReasonRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionResponse:
    try:
        return AccountActionResponse(
            **disable_participant(db, public_id=public_id, researcher=_actor(db), reason=payload.reason)
        )
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.post("/dashboard/participants/{public_id}/enable", response_model=AccountActionResponse)
def gv_enable(
    public_id: str,
    payload: AccountReasonRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionResponse:
    try:
        return AccountActionResponse(
            **enable_participant(db, public_id=public_id, researcher=_actor(db), reason=payload.reason)
        )
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.post("/dashboard/participants/{public_id}/remove-account", response_model=AccountActionResponse)
def gv_remove_account(
    public_id: str,
    payload: RemoveAccountRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionResponse:
    try:
        return AccountActionResponse(
            **remove_participant_access(
                db,
                public_id=public_id,
                researcher=_actor(db),
                reason=payload.reason,
                confirmation_public_id=payload.confirmation_public_id,
            )
        )
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.get("/dashboard/participants/{public_id}/account-actions", response_model=AccountActionListResponse)
def gv_account_actions(
    public_id: str,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> AccountActionListResponse:
    try:
        items = list_account_actions(db, public_id=public_id)
        return AccountActionListResponse(items=[AccountActionRecord(**item) for item in items])
    except AccountError as exc:
        raise _account_http_error(exc) from exc


@router.post(
    "/dashboard/participants/{public_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def gv_send_message(
    public_id: str,
    payload: SendMessageRequest,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> MessageResponse:
    try:
        return MessageResponse(
            **send_participant_message(
                db,
                public_id=public_id,
                researcher=_actor(db),
                subject=payload.subject,
                body=payload.body,
            )
        )
    except MessageError as exc:
        raise _message_http_error(exc) from exc


@router.get("/dashboard/participants/{public_id}/messages", response_model=MessagePage)
def gv_list_messages(
    public_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> MessagePage:
    try:
        items, total = list_researcher_participant_messages(db, public_id=public_id, limit=limit, offset=offset)
        return MessagePage(
            items=[MessageResponse(**item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    except MessageError as exc:
        raise _message_http_error(exc) from exc


@router.get("/consents", response_model=ResearcherConsentPage)
def gv_list_consents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> ResearcherConsentPage:
    items, total = list_consents(db, limit=limit, offset=offset, search=search, sort_order=sort_order)
    return ResearcherConsentPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/consents/{consent_id}/pdf")
def gv_view_consent_pdf(
    consent_id: UUID,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> Response:
    try:
        record = get_consent(db, consent_id)
        filename = safe_participant_filename(record.participant.public_id)
        pdf_bytes = delivery_bytes_for_record(record)
    except ResearcherConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ConsentPdfError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"', "Cache-Control": "private, no-store"},
    )


@router.get("/consents/{consent_id}/download")
def gv_download_consent_pdf(
    consent_id: UUID,
    _vault: dict = Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
) -> Response:
    try:
        record = get_consent(db, consent_id)
        filename = safe_participant_filename(record.participant.public_id)
        pdf_bytes = delivery_bytes_for_record(record)
    except ResearcherConsentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except ConsentPdfError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"},
    )


@router.post("/participants/{public_id}/feedback/release")
def gv_release_feedback(
    public_id: str,
    _vault=Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        participant = get_participant_by_public_id(db, public_id)
        snapshot = release_participant_feedback(db, participant=participant, researcher_id=_actor(db).id)
    except (ConsentError, ParticipantFeedbackError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"status": snapshot.status, "snapshot_id": str(snapshot.id)}


@router.post("/participants/{public_id}/feedback/refresh")
def gv_refresh_feedback(
    public_id: str,
    _vault=Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        participant = get_participant_by_public_id(db, public_id)
        snapshot = refresh_participant_feedback(db, participant=participant, researcher_id=_actor(db).id)
    except (ConsentError, ParticipantFeedbackError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"status": snapshot.status, "snapshot_id": str(snapshot.id)}


@router.post("/participants/{public_id}/feedback/revoke")
def gv_revoke_feedback(
    public_id: str,
    _vault=Depends(get_current_golden_vault),
    db: Session = Depends(get_db),
):
    try:
        participant = get_participant_by_public_id(db, public_id)
        snapshot = revoke_participant_feedback(db, participant=participant, researcher_id=_actor(db).id)
    except (ConsentError, ParticipantFeedbackError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return {"status": snapshot.status, "snapshot_id": str(snapshot.id)}


def _bulk_http(handler, payload, researcher, db):
    try:
        return BulkActionResult(**handler(db, researcher=researcher, **payload.model_dump()))
    except BulkActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.post("/participants/bulk/message", response_model=BulkActionResult)
def gv_bulk_message(payload: BulkMessageRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(
        bulk_message,
        payload,
        _actor(db),
        db,
    )


@router.post("/participants/bulk/email", response_model=BulkActionResult)
def gv_bulk_email(payload: BulkEmailRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_email, payload, _actor(db), db)


@router.post("/participants/bulk/suspend", response_model=BulkActionResult)
def gv_bulk_suspend(payload: BulkSuspendRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_suspend, payload, _actor(db), db)


@router.post("/participants/bulk/reactivate", response_model=BulkActionResult)
def gv_bulk_reactivate(payload: BulkReactivateRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_reactivate, payload, _actor(db), db)


@router.post("/participants/bulk/remove", response_model=BulkActionResult)
def gv_bulk_remove(payload: BulkRemoveRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_remove, payload, _actor(db), db)


@router.post("/participants/feedback/release-bulk", response_model=BulkActionResult)
def gv_bulk_release_feedback(payload: BulkSelectionRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_release_feedback, payload, _actor(db), db)


@router.post("/participants/feedback/revoke-bulk", response_model=BulkActionResult)
def gv_bulk_revoke_feedback(payload: BulkSelectionRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_revoke_feedback, payload, _actor(db), db)


@router.post("/participants/feedback/refresh-bulk", response_model=BulkActionResult)
def gv_bulk_refresh_feedback(payload: BulkSelectionRequest, _vault=Depends(get_current_golden_vault), db: Session = Depends(get_db)):
    return _bulk_http(bulk_refresh_feedback, payload, _actor(db), db)
