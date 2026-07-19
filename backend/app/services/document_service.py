"""Researcher-only Form 4 document management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.form4_record import Form4Record
from app.models.generated_study_document import GeneratedStudyDocument
from app.models.researcher import Researcher
from app.services.audit_service import record_audit_event
from app.services.consent_service import resolve_active_protocol
from app.services.document_status_service import DocumentStatusError, validate_generate_transition, validate_status_update
from app.services.pdf_form_service import (
    BACKEND_ROOT,
    DOCUMENTS_DIR,
    generate_form4_pdf,
    load_template_metadata,
)

FORM4_FIELDS = (
    "student_researcher_names",
    "project_title",
    "adult_sponsor",
    "adult_sponsor_contact",
    "research_plan_submitted",
    "surveys_attached",
    "published_instruments_legally_obtained",
    "informed_consent_attached",
    "qualified_scientist",
    "full_committee_review",
    "risk_level",
    "qualified_scientist_required",
    "risk_assessment_required",
    "minor_assent_required",
    "parental_permission_required",
    "adult_informed_consent_required",
    "signer_records",
)


class DocumentError(Exception):
    def __init__(self, message: str, status_code: int = 404, error_code: str = "DOCUMENT_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def _template_info() -> dict[str, str]:
    metadata = load_template_metadata()
    return {
        "template_id": metadata.get("template_id", "isef-human-participants-form4-2023-2024"),
        "template_version": metadata.get("template_version", "isef-form4-2023-2024-official"),
        "template_sha256": metadata.get("sha256", ""),
    }


def _completion_percentage(record: Form4Record) -> float:
    values = [
        record.student_researcher_names,
        record.project_title,
        record.adult_sponsor,
        record.adult_sponsor_contact,
        record.research_plan_submitted,
        record.surveys_attached,
        record.published_instruments_legally_obtained,
        record.informed_consent_attached,
        record.qualified_scientist,
        record.full_committee_review,
        record.risk_level,
        record.qualified_scientist_required,
        record.risk_assessment_required,
        record.minor_assent_required,
        record.parental_permission_required,
        record.adult_informed_consent_required,
    ]
    filled = sum(1 for value in values if value not in (None, "", []))
    return round((filled / len(values)) * 100, 1)


def _serialize_summary(document: GeneratedStudyDocument, record: Form4Record | None) -> dict[str, Any]:
    protocol = document.protocol
    return {
        "id": document.id,
        "document_type": document.document_type,
        "protocol_version": protocol.version if protocol else "",
        "template_version": document.template_version,
        "template_id": document.template_id,
        "status": document.status,
        "project_title": record.project_title if record else None,
        "completion_percentage": _completion_percentage(record) if record else 0.0,
        "generated_at": document.generated_at,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "has_generated_pdf": bool(document.artifact_hash),
    }


def _get_document(db: Session, document_id: UUID) -> GeneratedStudyDocument:
    document = db.execute(
        select(GeneratedStudyDocument)
        .options(selectinload(GeneratedStudyDocument.protocol), selectinload(GeneratedStudyDocument.form4_record))
        .where(GeneratedStudyDocument.id == document_id)
    ).scalar_one_or_none()
    if document is None:
        raise DocumentError("Document not found", status_code=404, error_code="NOT_FOUND")
    return document


def _serialize_detail(document: GeneratedStudyDocument, record: Form4Record | None) -> dict[str, Any]:
    summary = _serialize_summary(document, record)
    form4 = None
    if record is not None:
        form4 = {field: getattr(record, field) for field in FORM4_FIELDS}
    return {
        **summary,
        "protocol_id": document.protocol_id,
        "artifact_hash": document.artifact_hash,
        "form4": form4,
    }


def create_form4_draft(
    db: Session,
    *,
    researcher: Researcher,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    protocol = resolve_active_protocol(db)
    template = _template_info()
    document = GeneratedStudyDocument(
        id=uuid.uuid4(),
        document_type="form_4",
        protocol_id=protocol.id,
        template_version=template["template_version"],
        template_id=template["template_id"],
        template_sha256=template["template_sha256"],
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    record = Form4Record(
        id=uuid.uuid4(),
        document_id=document.id,
        project_title=(payload or {}).get("project_title"),
        student_researcher_names=(payload or {}).get("student_researcher_names"),
        adult_sponsor=(payload or {}).get("adult_sponsor"),
        adult_sponsor_contact=(payload or {}).get("adult_sponsor_contact"),
        signer_records=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(document)
    db.add(record)
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        document_id=document.id,
        event_type="document_created",
        metadata={"document_type": "form_4", "template_id": template["template_id"]},
    )
    db.commit()
    db.refresh(document)
    db.refresh(record)
    return _serialize_detail(document, record)


def update_form4_record(
    db: Session,
    *,
    document_id: UUID,
    researcher: Researcher,
    payload: dict[str, Any],
) -> dict[str, Any]:
    document = _get_document(db, document_id)
    if document.document_type != "form_4":
        raise DocumentError("Document is not a Form 4 record", status_code=422)
    if document.status == "approved":
        raise DocumentError("Approved documents cannot be edited", status_code=422, error_code="DOCUMENT_LOCKED")
    record = document.form4_record
    if record is None:
        raise DocumentError("Form 4 record not found", status_code=404)

    for field in FORM4_FIELDS:
        if field in payload:
            value = payload[field]
            if field == "signer_records":
                setattr(record, field, [item for item in (value or [])])
            else:
                setattr(record, field, value)
    record.updated_at = datetime.now(UTC)
    document.updated_at = datetime.now(UTC)
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        document_id=document.id,
        event_type="form4_updated",
    )
    db.commit()
    db.refresh(document)
    db.refresh(record)
    return _serialize_detail(document, record)


def update_document_status(
    db: Session,
    *,
    document_id: UUID,
    researcher: Researcher,
    target_status: str,
    confirm_approved: bool = False,
) -> dict[str, Any]:
    document = _get_document(db, document_id)
    record = document.form4_record
    try:
        validate_status_update(
            document,
            record,
            target_status=target_status,
            confirm_approved=confirm_approved,
        )
    except DocumentStatusError as exc:
        raise DocumentError(exc.message, status_code=exc.status_code, error_code=exc.error_code) from exc

    document.status = target_status
    document.updated_at = datetime.now(UTC)
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        document_id=document.id,
        event_type="document_status_changed",
        metadata={"status": target_status},
    )
    db.commit()
    db.refresh(document)
    return _serialize_detail(document, record)


def list_documents(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(GeneratedStudyDocument, Form4Record)
        .outerjoin(Form4Record, Form4Record.document_id == GeneratedStudyDocument.id)
        .options(selectinload(GeneratedStudyDocument.protocol))
        .order_by(GeneratedStudyDocument.created_at.desc())
    ).all()
    return [_serialize_summary(document, record) for document, record in rows]


def get_document_detail(db: Session, document_id: UUID) -> dict[str, Any]:
    document = _get_document(db, document_id)
    record = document.form4_record
    if record is None and document.document_type == "form_4":
        raise DocumentError("Form 4 record not found", status_code=404)
    return _serialize_detail(document, record)


def generate_document_pdf(
    db: Session,
    *,
    document_id: UUID,
    researcher: Researcher,
) -> dict[str, Any]:
    document = _get_document(db, document_id)
    if document.document_type != "form_4":
        raise DocumentError("Only Form 4 documents can be generated", status_code=422)
    record = document.form4_record
    if record is None:
        raise DocumentError("Form 4 record not found", status_code=404)
    try:
        validate_generate_transition(document)
    except DocumentStatusError as exc:
        raise DocumentError(exc.message, status_code=exc.status_code, error_code=exc.error_code) from exc

    artifact_path, artifact_hash = generate_form4_pdf(document.id, record)
    document.artifact_path = f"generated_documents/{document.id}/form-4.pdf"
    document.artifact_hash = artifact_hash
    document.generated_by_researcher_id = researcher.id
    document.generated_at = datetime.now(UTC)
    document.updated_at = datetime.now(UTC)
    if document.status == "draft":
        document.status = "awaiting_irb"

    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher.id,
        document_id=document.id,
        event_type="pdf_generated",
        metadata={"artifact_hash": artifact_hash},
    )
    db.commit()
    db.refresh(document)
    return {
        "document_id": document.id,
        "status": document.status,
        "artifact_hash": artifact_hash,
        "generated_at": document.generated_at,
    }


def resolve_download_path(db: Session, document_id: UUID) -> Path:
    document = _get_document(db, document_id)
    if not document.artifact_path:
        raise DocumentError("Document PDF has not been generated", status_code=404)
    candidate = (BACKEND_ROOT / document.artifact_path).resolve()
    allowed_root = DOCUMENTS_DIR.resolve()
    templates_root = (BACKEND_ROOT / "templates").resolve()
    if templates_root in candidate.parents or candidate == templates_root:
        raise DocumentError("Invalid document path", status_code=400, error_code="PATH_FORBIDDEN")
    if allowed_root not in candidate.parents:
        raise DocumentError("Invalid document path", status_code=400, error_code="PATH_TRAVERSAL")
    if not candidate.exists() or not candidate.is_file():
        raise DocumentError("Generated PDF not found", status_code=404)
    return candidate
