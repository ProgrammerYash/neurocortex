"""Backfill synthetic enrollment dates and consent signing timestamps (idempotent)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.consent_record import ConsentRecord
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant
from app.services.consent_content import CONSENT_VERSION
from app.services.consent_pdf_service import ConsentPdfError, generate_consent_pdf
from app.services.participant_enrollment import (
    enrollment_datetime_from_study_date,
    resolve_synthetic_enrollment_at,
)
from app.services.signature_style import SIGNATURE_METHOD_TYPED


def repair_synthetic_participant_enrollment(db: Session, *, participant_id) -> bool:
    participant = db.get(Participant, participant_id)
    if participant is None:
        return False
    override = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant_id)
    ).scalar_one_or_none()
    if override is None or not override.is_synthetic_generated:
        return False

    enrollment_at = resolve_synthetic_enrollment_at(db, participant=participant, override=override)
    if enrollment_at is None:
        return False

    changed = False
    if override.synthetic_enrollment_at is None:
        override.synthetic_enrollment_at = enrollment_at
        changed = True
    if participant.created_at > enrollment_at:
        db.execute(
            update(Participant)
            .where(Participant.id == participant.id)
            .values(created_at=enrollment_at)
        )
        changed = True

    record = db.execute(
        select(ConsentRecord)
        .where(
            ConsentRecord.participant_id == participant.id,
            ConsentRecord.consent_version == CONSENT_VERSION,
            ConsentRecord.revoked_at.is_(None),
        )
        .limit(1)
    ).scalar_one_or_none()
    if record is not None and record.is_synthetic_demo_record:
        if record.participant_signed_at != enrollment_at or record.guardian_signed_at != enrollment_at:
            db.execute(
                update(ConsentRecord)
                .where(ConsentRecord.id == record.id)
                .values(
                    participant_signed_at=enrollment_at,
                    guardian_signed_at=enrollment_at,
                    created_at=enrollment_at,
                )
            )
            changed = True
        if record.signature_method == SIGNATURE_METHOD_TYPED and not record.repaired_delivery_pdf_bytes:
            try:
                participant_text = record.participant_signature_text or record.participant_printed_name
                guardian_text = record.guardian_signature_text or record.guardian_printed_name
                pdf_bytes, pdf_sha256 = generate_consent_pdf(
                    participant_printed_name=record.participant_printed_name,
                    guardian_printed_name=record.guardian_printed_name,
                    participant_signature_text=participant_text,
                    guardian_signature_text=guardian_text,
                    participant_signed_at=enrollment_at,
                    guardian_signed_at=enrollment_at,
                    is_synthetic_demo_record=False,
                )
                if hashlib.sha256(pdf_bytes).hexdigest() != record.pdf_sha256:
                    db.execute(
                        update(ConsentRecord)
                        .where(ConsentRecord.id == record.id)
                        .values(
                            pdf_bytes=pdf_bytes,
                            pdf_sha256=pdf_sha256,
                        )
                    )
                    changed = True
            except ConsentPdfError:
                pass

    db.flush()
    return changed


def repair_all_synthetic_enrollments(db: Session, *, limit: int = 500) -> dict[str, int]:
    overrides = db.execute(
        select(GoldenDemoOverride)
        .where(GoldenDemoOverride.is_synthetic_generated.is_(True))
        .limit(limit)
    ).scalars().all()
    repaired = 0
    for override in overrides:
        if repair_synthetic_participant_enrollment(db, participant_id=override.participant_id):
            repaired += 1
    return {"scanned": len(overrides), "repaired": repaired}


def enrollment_at_for_batch_start(start_date) -> datetime:
    return enrollment_datetime_from_study_date(start_date)
