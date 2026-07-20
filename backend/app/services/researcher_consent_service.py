"""Researcher-only consent metadata and archive helpers."""

from __future__ import annotations

import csv
import hashlib
import io
import re
import tempfile
import zipfile
from pathlib import PurePosixPath
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.consent_record import ConsentRecord
from app.models.participant import Participant


class ResearcherConsentError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def serialize_consent(record: ConsentRecord) -> dict:
    return {
        "id": record.id,
        "participant_id": record.participant.public_id,
        "participant_printed_name": record.participant_printed_name,
        "guardian_printed_name": record.guardian_printed_name,
        "participant_signed_at": record.participant_signed_at,
        "guardian_signed_at": record.guardian_signed_at,
        "consent_version": record.consent_version,
        "survey_version": record.survey_version,
        "status": "revoked" if record.revoked_at else "active",
    }


def list_consents(
    db: Session,
    *,
    limit: int,
    offset: int,
    search: str | None,
    sort_order: str,
) -> tuple[list[dict], int]:
    filters = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                Participant.public_id.ilike(term),
                ConsentRecord.participant_printed_name.ilike(term),
            )
        )
    count_query = (
        select(func.count(ConsentRecord.id))
        .select_from(ConsentRecord)
        .join(Participant)
    )
    query = (
        select(ConsentRecord)
        .join(Participant)
        .options(joinedload(ConsentRecord.participant))
    )
    if filters:
        count_query = count_query.where(*filters)
        query = query.where(*filters)
    ordering = (
        asc(ConsentRecord.participant_signed_at)
        if sort_order == "asc"
        else desc(ConsentRecord.participant_signed_at)
    )
    records = db.execute(
        query.order_by(ordering, ConsentRecord.id).limit(limit).offset(offset)
    ).scalars().all()
    total = db.execute(count_query).scalar_one()
    return [serialize_consent(record) for record in records], int(total)


def get_consent(db: Session, consent_id: UUID) -> ConsentRecord:
    record = db.execute(
        select(ConsentRecord)
        .options(joinedload(ConsentRecord.participant))
        .where(ConsentRecord.id == consent_id)
    ).scalar_one_or_none()
    if record is None:
        raise ResearcherConsentError("Consent record not found", status_code=404)
    if not record.pdf_bytes.startswith(b"%PDF"):
        raise ResearcherConsentError("Stored consent document is invalid", status_code=500)
    if hashlib.sha256(record.pdf_bytes).hexdigest() != record.pdf_sha256:
        raise ResearcherConsentError("Stored consent document failed integrity check", status_code=500)
    return record


def safe_participant_filename(public_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", public_id).strip("-_")[:64]
    if not safe:
        raise ResearcherConsentError("Participant identifier cannot form a safe filename", status_code=500)
    filename = f"{safe}-consent.pdf"
    if PurePosixPath(filename).name != filename:
        raise ResearcherConsentError("Unsafe consent filename", status_code=500)
    return filename


def _csv_safe(value: object) -> str:
    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def build_all_consents_zip(db: Session) -> tempfile.SpooledTemporaryFile:
    records = db.execute(
        select(ConsentRecord)
        .options(joinedload(ConsentRecord.participant))
        .order_by(ConsentRecord.participant_signed_at.asc(), ConsentRecord.id.asc())
    ).scalars().all()

    prepared: list[tuple[ConsentRecord, str]] = []
    filename_counts: dict[str, int] = {}
    for record in records:
        if (
            not record.pdf_bytes.startswith(b"%PDF")
            or hashlib.sha256(record.pdf_bytes).hexdigest() != record.pdf_sha256
        ):
            raise ResearcherConsentError("A stored consent document failed integrity check", 500)
        base_name = safe_participant_filename(record.participant.public_id)
        count = filename_counts.get(base_name, 0)
        filename_counts[base_name] = count + 1
        if count:
            stem = base_name[:-4]
            version = re.sub(r"[^A-Za-z0-9_-]", "-", record.consent_version)[:32]
            base_name = f"{stem}-{version}-{count + 1}.pdf"
        if PurePosixPath(base_name).name != base_name:
            raise ResearcherConsentError("Unsafe consent archive filename", 500)
        prepared.append((record, base_name))

    manifest_buffer = io.StringIO(newline="")
    writer = csv.writer(manifest_buffer, lineterminator="\n")
    writer.writerow(
        [
            "Participant ID",
            "Participant printed name",
            "Guardian printed name",
            "Student signed date",
            "Guardian signed date",
            "Consent version",
            "Survey version",
            "PDF SHA-256",
        ]
    )
    for record, _filename in prepared:
        writer.writerow(
            [
                _csv_safe(record.participant.public_id),
                _csv_safe(record.participant_printed_name),
                _csv_safe(record.guardian_printed_name),
                record.participant_signed_at.isoformat(),
                record.guardian_signed_at.isoformat(),
                record.consent_version,
                record.survey_version,
                record.pdf_sha256,
            ]
        )

    spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    try:
        with zipfile.ZipFile(spool, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for record, filename in prepared:
                archive.writestr(filename, record.pdf_bytes)
            archive.writestr("manifest.csv", manifest_buffer.getvalue().encode("utf-8-sig"))
        spool.seek(0)
        return spool
    except Exception:
        spool.close()
        raise
