"""Regenerate delivery consent PDFs with typed signatures while preserving originals."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.participant import Participant
from app.models.researcher import Researcher
from app.services.audit_service import record_audit_event
from app.services.consent_pdf_service import ConsentPdfError, delivery_pdf_bytes, generate_consent_pdf
from app.services.consent_content import CONSENT_VERSION
from app.services.researcher_consent_service import ResearcherConsentError, get_consent
from app.services.signature_style import SIGNATURE_METHOD_DRAWN_LEGACY, SIGNATURE_METHOD_TYPED

REPAIR_VERSION = "typed-signature-v1"


class LegacyConsentRepairError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _missing_name_field(record: ConsentRecord) -> str | None:
    if not (record.participant_printed_name or "").strip():
        return "participant_printed_name"
    if not (record.guardian_printed_name or "").strip():
        return "guardian_printed_name"
    return None


def consent_signature_metadata(record: ConsentRecord) -> dict[str, Any]:
    missing = _missing_name_field(record)
    eligible = (
        record.revoked_at is None
        and record.consent_version == CONSENT_VERSION
        and record.signature_method == SIGNATURE_METHOD_DRAWN_LEGACY
        and missing is None
        and record.legacy_signature_repaired_at is None
        and not record.repaired_delivery_pdf_bytes
    )
    return {
        "signature_format": record.signature_method,
        "legacy_signature_repair_eligible": eligible,
        "legacy_signature_repaired": record.legacy_signature_repaired_at is not None,
        "legacy_signature_repaired_at": record.legacy_signature_repaired_at,
        "legacy_signature_repair_version": record.legacy_signature_repair_version,
    }


def fix_legacy_consent_signature(
    db: Session,
    *,
    participant: Participant,
    researcher: Researcher,
) -> dict[str, Any]:
    from sqlalchemy import select

    record = db.execute(
        select(ConsentRecord)
        .where(
            ConsentRecord.participant_id == participant.id,
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if record is None:
        raise LegacyConsentRepairError("No active consent record found", status_code=404)

    missing = _missing_name_field(record)
    if missing:
        raise LegacyConsentRepairError(
            f"Consent repair requires stored printed names; missing {missing}.",
            status_code=422,
        )

    if record.signature_method == SIGNATURE_METHOD_TYPED:
        raise LegacyConsentRepairError("Consent already uses typed signatures.", status_code=409)

    if record.legacy_signature_repaired_at and record.repaired_delivery_pdf_bytes:
        return {
            "ok": True,
            "participant_id": participant.public_id,
            "consent_id": str(record.id),
            "repaired": False,
            "already_repaired": True,
            "original_signed_at": record.participant_signed_at,
            "delivery_pdf_hash": record.repaired_delivery_pdf_sha256,
            "repair_version": record.legacy_signature_repair_version or REPAIR_VERSION,
            **consent_signature_metadata(record),
        }

    original_delivery_hash = record.repaired_delivery_pdf_sha256
    try:
        corrected, pdf_hash = generate_consent_pdf(
            participant_printed_name=record.participant_printed_name,
            guardian_printed_name=record.guardian_printed_name,
            participant_signature_text=record.participant_printed_name,
            guardian_signature_text=record.guardian_printed_name,
            participant_signed_at=record.participant_signed_at,
            guardian_signed_at=record.guardian_signed_at,
            is_synthetic_demo_record=False,
        )
        delivery = delivery_pdf_bytes(corrected)
        delivery_hash = hashlib.sha256(delivery).hexdigest()
    except ConsentPdfError as exc:
        raise LegacyConsentRepairError(str(exc), status_code=422) from exc

    if delivery_hash != pdf_hash:
        delivery_hash = hashlib.sha256(delivery).hexdigest()

    from datetime import UTC, datetime

    record.legacy_signature_repaired_at = datetime.now(UTC)
    record.legacy_signature_repaired_by = researcher.id
    record.legacy_signature_repair_version = REPAIR_VERSION
    record.repaired_delivery_pdf_bytes = delivery
    record.repaired_delivery_pdf_sha256 = delivery_hash
    db.flush()

    record_audit_event(
        db,
        actor_type="researcher",
        event_type="consent.legacy_signature_repaired",
        participant_id=participant.id,
        document_id=record.id,
        metadata={
            "participant_public_id": participant.public_id,
            "consent_id": str(record.id),
            "previous_delivery_pdf_hash": original_delivery_hash,
            "new_delivery_pdf_hash": delivery_hash,
            "repair_version": REPAIR_VERSION,
            "reason": "legacy drawn signature modernization",
        },
    )

    return {
        "ok": True,
        "participant_id": participant.public_id,
        "consent_id": str(record.id),
        "repaired": True,
        "already_repaired": False,
        "original_signed_at": record.participant_signed_at,
        "delivery_pdf_hash": delivery_hash,
        "repair_version": REPAIR_VERSION,
        **consent_signature_metadata(record),
    }


def delivery_bytes_for_record(record: ConsentRecord) -> bytes:
    if record.repaired_delivery_pdf_bytes and record.repaired_delivery_pdf_sha256:
        if hashlib.sha256(record.repaired_delivery_pdf_bytes).hexdigest() == record.repaired_delivery_pdf_sha256:
            return delivery_pdf_bytes(record.repaired_delivery_pdf_bytes)
    return delivery_consent_pdf_for_record_inner(record)


def delivery_consent_pdf_for_record_inner(record: ConsentRecord) -> bytes:
    from app.services.consent_pdf_service import _delivery_consent_pdf_for_record_default

    return _delivery_consent_pdf_for_record_default(record)
