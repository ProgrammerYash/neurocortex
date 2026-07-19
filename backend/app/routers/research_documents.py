from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_researcher
from app.models.researcher import Researcher
from app.schemas.documents import (
    DocumentDetail,
    DocumentStatusUpdateRequest,
    DocumentSummary,
    Form4DraftRequest,
    Form4UpdateRequest,
    GenerateDocumentResponse,
)
from app.services.audit_service import record_audit_event
from app.services.document_service import (
    DocumentError,
    create_form4_draft,
    generate_document_pdf,
    get_document_detail,
    list_documents,
    resolve_download_path,
    update_document_status,
    update_form4_record,
)

router = APIRouter(prefix="/research/documents", tags=["research-documents"])


def _document_http_error(exc: DocumentError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"message": exc.message, "error_code": exc.error_code},
    )


@router.post("/form-4/draft", response_model=DocumentDetail, status_code=status.HTTP_201_CREATED)
def create_form4_draft_endpoint(
    payload: Form4DraftRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    try:
        return create_form4_draft(db, researcher=researcher, payload=payload.model_dump())
    except DocumentError as exc:
        raise _document_http_error(exc) from exc


@router.put("/form-4/{document_id}", response_model=DocumentDetail)
def update_form4_endpoint(
    document_id: UUID,
    payload: Form4UpdateRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    try:
        return update_form4_record(
            db,
            document_id=document_id,
            researcher=researcher,
            payload=payload.model_dump(exclude_unset=True),
        )
    except DocumentError as exc:
        raise _document_http_error(exc) from exc


@router.put("/form-4/{document_id}/status", response_model=DocumentDetail)
def update_form4_status_endpoint(
    document_id: UUID,
    payload: DocumentStatusUpdateRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    try:
        return update_document_status(
            db,
            document_id=document_id,
            researcher=researcher,
            target_status=payload.status,
            confirm_approved=payload.confirm_approved,
        )
    except DocumentError as exc:
        raise _document_http_error(exc) from exc


@router.get("", response_model=list[DocumentSummary])
def list_documents_endpoint(
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> list[DocumentSummary]:
    return list_documents(db)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document_endpoint(
    document_id: UUID,
    _researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> DocumentDetail:
    try:
        return get_document_detail(db, document_id)
    except DocumentError as exc:
        raise _document_http_error(exc) from exc


@router.post("/form-4/{document_id}/generate", response_model=GenerateDocumentResponse)
def generate_form4_endpoint(
    document_id: UUID,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
) -> GenerateDocumentResponse:
    try:
        return generate_document_pdf(db, document_id=document_id, researcher=researcher)
    except DocumentError as exc:
        raise _document_http_error(exc) from exc


@router.get("/{document_id}/download")
def download_document_endpoint(
    document_id: UUID,
    researcher: Researcher = Depends(get_current_researcher),
    db: Session = Depends(get_db),
):
    try:
        path = resolve_download_path(db, document_id)
        record_audit_event(
            db,
            actor_type="researcher",
            actor_id=researcher.id,
            document_id=document_id,
            event_type="pdf_downloaded",
        )
        db.commit()
        return FileResponse(
            path,
            media_type="application/pdf",
            filename="form-4-administrative-draft.pdf",
            headers={"Cache-Control": "no-store"},
        )
    except DocumentError as exc:
        raise _document_http_error(exc) from exc
