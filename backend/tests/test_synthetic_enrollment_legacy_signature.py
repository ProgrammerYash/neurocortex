"""Synthetic enrollment dates and legacy consent signature repair."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import io

from pypdf import PdfReader
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.researcher import Researcher
from tests.test_golden_fake_users import vault_env, vault_headers
from tests.test_researcher_dashboard import researcher_headers

from app.constants.study_title import STUDY_PROJECT_TITLE
from app.services.consent_pdf_service import generate_consent_pdf, pdf_signing_date
from app.services.legacy_consent_signature_service import (
    REPAIR_VERSION,
    consent_signature_metadata,
    fix_legacy_consent_signature,
)
from app.services.participant_enrollment import enrollment_datetime_from_study_date
from app.services.synthetic_enrollment_repair import repair_all_synthetic_enrollments


@pytest.fixture()
def researcher(db: Session) -> Researcher:
    row = Researcher(display_name="Legacy Repair Tester", email=f"{uuid4()}@example.test")
    db.add(row)
    db.commit()
    return row


def test_enrollment_datetime_from_study_date_preserves_calendar_day():
    start = date(2026, 5, 29)
    enrollment_at = enrollment_datetime_from_study_date(start)
    assert pdf_signing_date(enrollment_at) == "05/29/26"


def test_synthetic_fake_user_uses_historical_start_in_dashboard(
    client,
    db: Session,
    vault_env,
    researcher,
):
    from datetime import date as date_cls

    start = date_cls.today() - timedelta(days=62)
    batch = client.post(
        "/v1/golden-vault/fake-users/generate",
        headers=vault_headers(),
        json={
            "total": 1,
            "start_date": start.isoformat(),
            "daily": 1,
            "weekly": 0,
            "two_days": 0,
            "four_days": 0,
        },
    )
    assert batch.status_code in {200, 201}
    batch_id = batch.json()["batchId"]
    for _ in range(30):
        proc = client.post(f"/v1/golden-vault/fake-users/batches/{batch_id}/process", headers=vault_headers())
        assert proc.status_code == 200
        if proc.json().get("status", "").startswith("completed"):
            break
    from app.services.researcher_dashboard_service import format_study_date

    client.post("/v1/golden-vault/synthetic-enrollment/repair", headers=vault_headers())
    expected_display = format_study_date(enrollment_datetime_from_study_date(start))
    dash = client.get(
        "/v1/golden-vault/management/dashboard/participants",
        headers=vault_headers(),
        params={"limit": 100, "participant_type": "synthetic_demo"},
    )
    assert dash.status_code == 200
    items = dash.json()["items"]
    assert any(row.get("joinedDisplay") == expected_display for row in items)


def test_legacy_signature_repair_eligibility(db: Session, researcher: Researcher):
    from app.models.consent_record import ConsentRecord
    from app.models.participant import Participant
    from app.utils.ids import generate_public_id
    from app.services.consent_content import CONSENT_VERSION, SURVEY_VERSION, EXPECTED_TEMPLATE_SHA256
    from tests.test_electronic_consent import signature_data_url
    import hashlib
    import uuid

    signed = datetime(2024, 6, 15, 16, 0, tzinfo=UTC)
    pdf_bytes, pdf_sha = generate_consent_pdf(
        participant_printed_name="Legacy Student",
        guardian_printed_name="Legacy Parent",
        participant_signature_png=signature_data_url(),
        guardian_signature_png=signature_data_url(),
        participant_signed_at=signed,
        guardian_signed_at=signed,
    )
    participant = Participant(
        public_id=generate_public_id(),
        pin_hash="x",
        grade="7th Grade",
        age_range="13",
        age_years=13,
        pet_choice="fox",
        study_frequency="daily",
    )
    db.add(participant)
    db.flush()
    record = ConsentRecord(
        id=uuid.uuid4(),
        participant_id=participant.id,
        participant_printed_name="Legacy Student",
        guardian_printed_name="Legacy Parent",
        participant_signed_at=signed,
        guardian_signed_at=signed,
        consent_version=CONSENT_VERSION,
        survey_version=SURVEY_VERSION,
        template_sha256=EXPECTED_TEMPLATE_SHA256,
        pdf_sha256=pdf_sha,
        pdf_bytes=pdf_bytes,
        signature_method="drawn_legacy",
        created_at=signed,
    )
    db.add(record)
    db.commit()
    meta = consent_signature_metadata(record)
    assert meta["legacy_signature_repair_eligible"] is True
    result = fix_legacy_consent_signature(db, participant=participant, researcher=researcher)
    db.commit()
    assert result["repaired"] is True
    assert result["repair_version"] == REPAIR_VERSION
    db.refresh(record)
    assert record.pdf_sha256 == pdf_sha
    assert hashlib.sha256(record.pdf_bytes).hexdigest() == pdf_sha
    delivery = record.repaired_delivery_pdf_bytes
    assert delivery
    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(delivery)).pages)
    assert STUDY_PROJECT_TITLE in text
    assert pdf_signing_date(signed) in text
    again = fix_legacy_consent_signature(db, participant=participant, researcher=researcher)
    assert again["already_repaired"] is True
