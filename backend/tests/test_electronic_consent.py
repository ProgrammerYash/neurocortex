from __future__ import annotations

import base64
import io
import zipfile
from datetime import date
from uuid import uuid4

import pytest
import pypdfium2
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.consent_record import ConsentRecord
from app.models.participant import Participant
from app.models.researcher import Researcher
from app.services.consent_content import (
    CONSENT_VERSION,
    EXPECTED_STATIC_VALUES,
    EXPECTED_TEMPLATE_SHA256,
    SURVEY_VERSION,
)
from app.services.consent_pdf_service import ConsentPdfError, validate_signature_png
from app.utils.security import (
    create_access_token,
    create_researcher_access_token,
    hash_pin,
)


def signature_data_url(*, width: int = 500, height: int = 120, blank: bool = False) -> str:
    image = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    if not blank:
        draw = ImageDraw.Draw(image)
        draw.line(
            (15, height - 20, width // 3, 15, width // 2, height - 25, width - 15, 20),
            fill=(0, 0, 0, 255),
            width=max(3, height // 18),
        )
    output = io.BytesIO()
    image.save(output, "PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


def registration_payload(**overrides) -> dict:
    payload = {
        "grade": "10th Grade",
        "age_range": "15-16",
        "age_consent_category": "under_18",
        "pet_choice": "fox",
        "pin": "2468",
        "pin_confirmation": "2468",
        "participant_printed_name": "Test Student",
        "guardian_printed_name": "Test Guardian",
        "participant_acknowledged": True,
        "guardian_acknowledged": True,
        "participant_signature_png": signature_data_url(),
        "guardian_signature_png": signature_data_url(width=480),
        "consent_version": CONSENT_VERSION,
        "survey_version": SURVEY_VERSION,
        "template_sha256": EXPECTED_TEMPLATE_SHA256,
        "idempotency_key": str(uuid4()),
    }
    payload.update(overrides)
    return payload


@pytest.fixture()
def db() -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def register(client: TestClient, payload: dict | None = None):
    return client.post("/v1/auth/participant/register", json=payload or registration_payload())


def test_current_consent_endpoint_matches_approved_template(client: TestClient):
    response = client.get("/v1/consent/current")
    assert response.status_code == 200
    body = response.json()
    assert body["template_sha256"] == EXPECTED_TEMPLATE_SHA256
    for key, value in EXPECTED_STATIC_VALUES.items():
        assert body[key] == value
    assert set(body) == {
        "consent_version",
        "survey_version",
        "template_sha256",
        "student_researcher",
        "project_title",
        "purpose",
        "participation_activities",
        "time_required",
        "potential_risks",
        "potential_benefits",
        "confidentiality",
        "questions_contact",
        "adult_sponsor",
        "adult_sponsor_contact",
        "voluntary_participation",
        "may_stop",
        "may_skip_questions",
        "signing_explanation",
        "participant_acknowledgment",
        "guardian_acknowledgment",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("participant_signature_png", None),
        ("guardian_signature_png", None),
        ("participant_acknowledged", False),
        ("guardian_acknowledged", False),
        ("participant_signature_png", "data:image/png;base64,not-valid"),
        ("guardian_signature_png", "data:image/jpeg;base64,AAAA"),
        ("participant_signature_png", signature_data_url(blank=True)),
        ("guardian_signature_png", signature_data_url(width=2049, height=16)),
    ],
)
def test_registration_rejects_missing_or_invalid_consent(
    client: TestClient,
    field: str,
    value,
):
    payload = registration_payload()
    if value is None:
        payload.pop(field)
    else:
        payload[field] = value
    assert register(client, payload).status_code == 422


def test_signature_validation_rejects_blank_and_oversized():
    with pytest.raises(ConsentPdfError, match="blank"):
        validate_signature_png(signature_data_url(blank=True), "Signature")
    with pytest.raises(ConsentPdfError, match="dimensions"):
        validate_signature_png(
            signature_data_url(width=2049, height=16),
            "Signature",
        )


def test_atomic_registration_pdf_content_hashes_and_idempotency(
    client: TestClient,
    db: Session,
):
    participant_count_before = db.execute(
        select(func.count()).select_from(Participant)
    ).scalar_one()
    payload = registration_payload()
    first = register(client, payload)
    assert first.status_code == 201, first.text
    second = register(client, payload)
    assert second.status_code == 201
    assert second.json()["public_id"] == first.json()["public_id"]

    participant_count = db.execute(select(func.count()).select_from(Participant)).scalar_one()
    records = db.execute(
        select(ConsentRecord).where(
            ConsentRecord.idempotency_key == payload["idempotency_key"]
        )
    ).scalars().all()
    assert participant_count == participant_count_before + 1
    assert len(records) == 1
    record = records[0]
    original_bytes = bytes(record.pdf_bytes)
    assert record.consent_version == CONSENT_VERSION
    assert record.survey_version == SURVEY_VERSION
    assert record.template_sha256 == EXPECTED_TEMPLATE_SHA256
    assert len(record.pdf_sha256) == 64
    assert original_bytes.startswith(b"%PDF")

    reader = PdfReader(io.BytesIO(original_bytes))
    assert len(reader.pages) >= 2
    assert not reader.get_fields()
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Test Student" in text
    assert "Test Guardian" in text
    assert record.participant_signed_at.strftime("%m/%d/%y") in text
    assert record.guardian_signed_at.strftime("%m/%d/%y") in text
    assert EXPECTED_STATIC_VALUES["project_title"] in text
    assert "NeuroCortex Survey/Questionnaire Appendix" in text
    assert "Major exam in the next 3 days?" in text
    rendered = pypdfium2.PdfDocument(original_bytes)
    try:
        assert len(rendered) == len(reader.pages)
        for page in rendered:
            image = page.render(scale=2).to_pil().convert("L")
            assert image.size == (1224, 1584)
            assert image.getextrema()[0] < 250
    finally:
        rendered.close()

    db.expire_all()
    unchanged = db.get(ConsentRecord, record.id)
    assert unchanged is not None
    assert bytes(unchanged.pdf_bytes) == original_bytes


def test_registration_rolls_back_when_pdf_generation_fails(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    before = db.execute(select(func.count()).select_from(Participant)).scalar_one()

    def fail(**_kwargs):
        raise RuntimeError("private failure")

    monkeypatch.setattr(
        "app.services.electronic_consent_service.generate_consent_pdf",
        fail,
    )
    response = register(client)
    assert response.status_code == 500
    assert "private failure" not in response.text
    after = db.execute(select(func.count()).select_from(Participant)).scalar_one()
    assert after == before
    assert db.execute(select(func.count()).select_from(ConsentRecord)).scalar_one() == 0


def test_completed_consent_pdf_is_immutable(client: TestClient, db: Session):
    assert register(client).status_code == 201
    record = db.execute(select(ConsentRecord)).scalar_one()
    record.pdf_bytes = b"%PDF-mutated"
    with pytest.raises(ValueError, match="immutable"):
        db.flush()
    db.rollback()


def test_existing_participant_is_blocked_then_can_complete_consent(
    client: TestClient,
    db: Session,
):
    participant = Participant(
        public_id=f"NC-LEGACY-{uuid4().hex[:6].upper()}",
        pin_hash=hash_pin("1357"),
        grade="11th Grade",
        age_range="15-16",
        age_consent_category="under_18",
        pet_choice="owl",
    )
    db.add(participant)
    db.commit()
    token = create_access_token(participant_id=participant.id, public_id=participant.public_id)
    headers = {"Authorization": f"Bearer {token}"}

    profile = client.get("/v1/participants/me", headers=headers)
    assert profile.json()["consent_required"] is True
    blocked = client.put(
        f"/v1/participants/me/sessions/{date.today().isoformat()}/modules/reaction",
        headers=headers,
        json={"payload": {"avg": 250}},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["error_code"] == "CONSENT_REQUIRED"

    payload = registration_payload()
    for key in (
        "grade",
        "age_range",
        "age_consent_category",
        "pet_choice",
        "pin",
        "pin_confirmation",
    ):
        payload.pop(key)
    completed = client.post("/v1/participants/me/consent", headers=headers, json=payload)
    assert completed.status_code == 200, completed.text
    assert completed.json()["consent_recorded"] is True
    assert client.get("/v1/participants/me", headers=headers).json()["consent_required"] is False
    allowed = client.put(
        f"/v1/participants/me/sessions/{date.today().isoformat()}/modules/reaction",
        headers=headers,
        json={
            "payload": {
                "avg": 300,
                "median": 290,
                "sd": 20,
                "min": 200,
                "max": 400,
                "missed": 0,
                "trials": 20,
            }
        },
    )
    assert allowed.status_code == 200, allowed.text


def test_researcher_metadata_pdf_download_zip_and_participant_denial(
    client: TestClient,
    db: Session,
):
    registered = register(client)
    assert registered.status_code == 201, registered.text
    participant_headers = {
        "Authorization": f"Bearer {registered.json()['access_token']}"
    }
    record = db.execute(select(ConsentRecord)).scalar_one()
    researcher = Researcher(display_name="Consent Tester", email=f"{uuid4()}@example.test")
    db.add(researcher)
    db.commit()
    researcher_headers = {
        "Authorization": "Bearer "
        + create_researcher_access_token(
            researcher_id=researcher.id,
            display_name=researcher.display_name,
        )
    }

    protected_paths = [
        "/v1/researcher/consents",
        f"/v1/researcher/consents/{record.id}/pdf",
        f"/v1/researcher/consents/{record.id}/download",
        "/v1/researcher/consents/download-all",
    ]
    for path in protected_paths:
        assert client.get(path, headers=participant_headers).status_code == 403

    listing = client.get("/v1/researcher/consents", headers=researcher_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert "pdf_bytes" not in listing.text
    assert listing.json()["items"][0]["participant_id"] == registered.json()["public_id"]

    inline = client.get(
        f"/v1/researcher/consents/{record.id}/pdf",
        headers=researcher_headers,
    )
    assert inline.status_code == 200
    assert inline.content.startswith(b"%PDF")
    assert inline.headers["cache-control"] == "private, no-store"
    assert inline.headers["x-content-type-options"] == "nosniff"
    assert inline.headers["content-disposition"].startswith("inline")

    download = client.get(
        f"/v1/researcher/consents/{record.id}/download",
        headers=researcher_headers,
    )
    assert download.status_code == 200
    assert download.headers["content-disposition"].startswith("attachment")

    archive_response = client.get(
        "/v1/researcher/consents/download-all",
        headers=researcher_headers,
    )
    assert archive_response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive_response.content)) as archive:
        names = archive.namelist()
        assert "manifest.csv" in names
        assert f"{registered.json()['public_id']}-consent.pdf" in names
        assert all("/" not in name and "\\" not in name for name in names)
        assert "PDF SHA-256" in archive.read("manifest.csv").decode("utf-8-sig")

    missing = client.get(
        f"/v1/researcher/consents/{uuid4()}/pdf",
        headers=researcher_headers,
    )
    assert missing.status_code == 404


def test_download_all_zero_records_returns_manifest_only_zip(
    client: TestClient,
    db: Session,
):
    researcher = Researcher(display_name="Empty Archive Tester")
    db.add(researcher)
    db.commit()
    headers = {
        "Authorization": "Bearer "
        + create_researcher_access_token(
            researcher_id=researcher.id,
            display_name=researcher.display_name,
        )
    }
    response = client.get("/v1/researcher/consents/download-all", headers=headers)
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["manifest.csv"]


def test_signature_request_body_limit(client: TestClient):
    response = client.post(
        "/v1/auth/participant/register",
        content=b"x" * 3_000_001,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
