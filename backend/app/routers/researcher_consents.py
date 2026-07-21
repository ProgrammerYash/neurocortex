from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.database import get_db
from app.deps import get_current_researcher
from app.models.researcher import Researcher
from app.schemas.consent import ResearcherConsentPage
from app.services.consent_pdf_service import ConsentPdfError, delivery_pdf_bytes
from app.services.researcher_consent_service import (
    ResearcherConsentError,
    build_all_consents_zip,
    get_consent,
    list_consents,
    safe_participant_filename,
)

router = APIRouter(prefix="/researcher/consents", tags=["researcher-consents"])

PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Content-Type-Options": "nosniff",
}


def _http_error(exc: ResearcherConsentError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get("", response_model=ResearcherConsentPage)
def get_consents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> ResearcherConsentPage:
    items, total = list_consents(
        db,
        limit=limit,
        offset=offset,
        search=search,
        sort_order=sort_order,
    )
    return ResearcherConsentPage(items=items, total=total, limit=limit, offset=offset)


# Keep this fixed path before dynamic consent-id routes.
@router.get("/download-all")
def download_all_consents(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    try:
        archive = build_all_consents_zip(db)
    except ResearcherConsentError as exc:
        raise _http_error(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Consent archive could not be generated") from exc
    filename = f"neurocortex-consents-{datetime.now(UTC).date().isoformat()}.zip"
    return StreamingResponse(
        archive,
        media_type="application/zip",
        headers={
            **PRIVATE_HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
        background=BackgroundTask(archive.close),
    )


@router.get("/{consent_id}/pdf")
def view_consent_pdf(
    consent_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> Response:
    try:
        record = get_consent(db, consent_id)
        filename = safe_participant_filename(record.participant.public_id)
        pdf_bytes = delivery_pdf_bytes(record.pdf_bytes)
    except ResearcherConsentError as exc:
        raise _http_error(exc) from exc
    except ConsentPdfError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            **PRIVATE_HEADERS,
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@router.get("/{consent_id}/download")
def download_consent_pdf(
    consent_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> Response:
    try:
        record = get_consent(db, consent_id)
        filename = safe_participant_filename(record.participant.public_id)
        pdf_bytes = delivery_pdf_bytes(record.pdf_bytes)
    except ResearcherConsentError as exc:
        raise _http_error(exc) from exc
    except ConsentPdfError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            **PRIVATE_HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
