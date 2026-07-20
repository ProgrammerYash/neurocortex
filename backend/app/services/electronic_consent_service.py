"""Transactional creation of current electronic consent records."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.participant import Participant
from app.services.audit_service import record_audit_event
from app.services.consent_content import (
    CONSENT_VERSION,
    EXPECTED_TEMPLATE_SHA256,
    SURVEY_VERSION,
)
from app.services.consent_pdf_service import ConsentPdfError, generate_consent_pdf


def current_consent_record(
    db: Session,
    participant_id: uuid.UUID,
) -> ConsentRecord | None:
    return db.execute(
        select(ConsentRecord).where(
            ConsentRecord.participant_id == participant_id,
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
    ).scalar_one_or_none()


def has_current_consent(db: Session, participant_id: uuid.UUID) -> bool:
    return current_consent_record(db, participant_id) is not None


def _validate_versions(payload: dict[str, Any]) -> None:
    from app.services.consent_service import ConsentError

    if payload.get("consent_version") != CONSENT_VERSION:
        raise ConsentError(
            "The consent form has changed. Review the current form and try again.",
            status_code=409,
            error_code="CONSENT_VERSION_MISMATCH",
        )
    if payload.get("survey_version") != SURVEY_VERSION:
        raise ConsentError(
            "The survey version has changed. Review the current form and try again.",
            status_code=409,
            error_code="SURVEY_VERSION_MISMATCH",
        )
    if payload.get("template_sha256") != EXPECTED_TEMPLATE_SHA256:
        raise ConsentError(
            "The consent template has changed. Review the current form and try again.",
            status_code=409,
            error_code="CONSENT_TEMPLATE_MISMATCH",
        )
    if payload.get("participant_acknowledged") is not True:
        raise ConsentError(
            "Student acknowledgment is required",
            status_code=422,
            error_code="PARTICIPANT_ACKNOWLEDGMENT_REQUIRED",
        )
    if payload.get("guardian_acknowledged") is not True:
        raise ConsentError(
            "Parent/guardian acknowledgment is required",
            status_code=422,
            error_code="GUARDIAN_ACKNOWLEDGMENT_REQUIRED",
        )


def create_consent_record_uncommitted(
    db: Session,
    *,
    participant: Participant,
    payload: dict[str, Any],
) -> ConsentRecord:
    """Create a record and compatibility events; the caller owns commit/rollback."""
    from app.services.consent_service import (
        ConsentError,
        _active_form_version,
        _append_event,
        get_age_category,
        resolve_active_protocol,
    )

    _validate_versions(payload)
    existing = current_consent_record(db, participant.id)
    if existing is not None:
        return existing

    idempotency_key = str(payload["idempotency_key"])
    replay = db.execute(
        select(ConsentRecord).where(ConsentRecord.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if replay is not None:
        if replay.participant_id == participant.id:
            return replay
        raise ConsentError(
            "Idempotency key has already been used",
            status_code=409,
            error_code="IDEMPOTENCY_KEY_REUSED",
        )

    signed_at = datetime.now(UTC)
    try:
        pdf_bytes, pdf_sha256 = generate_consent_pdf(
            participant_printed_name=payload["participant_printed_name"],
            guardian_printed_name=payload["guardian_printed_name"],
            participant_signature_png=payload["participant_signature_png"],
            guardian_signature_png=payload["guardian_signature_png"],
            participant_signed_at=signed_at,
            guardian_signed_at=signed_at,
        )
    except ConsentPdfError as exc:
        raise ConsentError(
            str(exc),
            status_code=422,
            error_code="CONSENT_PDF_INVALID",
        ) from exc
    except Exception as exc:
        raise ConsentError(
            "Consent document could not be generated",
            status_code=500,
            error_code="CONSENT_PDF_GENERATION_FAILED",
        ) from exc

    record = ConsentRecord(
        id=uuid.uuid4(),
        participant_id=participant.id,
        participant_printed_name=" ".join(payload["participant_printed_name"].split()),
        guardian_printed_name=" ".join(payload["guardian_printed_name"].split()),
        participant_signed_at=signed_at,
        guardian_signed_at=signed_at,
        consent_version=CONSENT_VERSION,
        survey_version=SURVEY_VERSION,
        template_sha256=EXPECTED_TEMPLATE_SHA256,
        pdf_sha256=pdf_sha256,
        pdf_bytes=pdf_bytes,
        idempotency_key=idempotency_key,
        created_at=signed_at,
    )
    db.add(record)
    db.flush()

    protocol = resolve_active_protocol(db)
    age_category = get_age_category(participant)
    common_metadata = {
        "source": "electronic_consent",
        "consent_version": CONSENT_VERSION,
        "survey_version": SURVEY_VERSION,
    }
    if age_category == "minor":
        assent_form = _active_form_version(
            db,
            protocol_id=protocol.id,
            form_type="participant_assent",
        )
        _append_event(
            db,
            participant=participant,
            protocol=protocol,
            event_type="assent_granted",
            status="granted",
            recorded_by="participant_self",
            consent_form_version_id=assent_form.id,
            metadata=common_metadata,
            acknowledged_at=signed_at,
        )
    else:
        adult_form = _active_form_version(
            db,
            protocol_id=protocol.id,
            form_type="adult_informed_consent",
        )
        _append_event(
            db,
            participant=participant,
            protocol=protocol,
            event_type="adult_consent_granted",
            status="granted",
            recorded_by="participant_self",
            consent_form_version_id=adult_form.id,
            metadata=common_metadata,
            acknowledged_at=signed_at,
        )

    parental_form = _active_form_version(
        db,
        protocol_id=protocol.id,
        form_type="parental_permission",
    )
    _append_event(
        db,
        participant=participant,
        protocol=protocol,
        event_type="parental_permission_granted",
        status="granted",
        recorded_by="guardian",
        consent_form_version_id=parental_form.id,
        metadata=common_metadata,
        acknowledged_at=signed_at,
    )
    record_audit_event(
        db,
        actor_type="participant",
        actor_id=participant.id,
        participant_id=participant.id,
        event_type="electronic_consent_recorded",
        metadata={
            "consent_version": CONSENT_VERSION,
            "survey_version": SURVEY_VERSION,
            "template_sha256": EXPECTED_TEMPLATE_SHA256,
            "pdf_sha256": pdf_sha256,
        },
    )
    return record


def complete_existing_participant_consent(
    db: Session,
    *,
    participant: Participant,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from app.services.consent_service import build_consent_status

    try:
        create_consent_record_uncommitted(db, participant=participant, payload=payload)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return build_consent_status(db, participant)
