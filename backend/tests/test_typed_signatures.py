from __future__ import annotations

import base64
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.services.consent_pdf_service import _pdf_contains_synthetic_marker, generate_consent_pdf
from app.services.consent_service import ConsentError
from app.services.electronic_consent_service import _resolve_signature_payload
from app.services.signature_style import typed_signature_png_bytes
from tests.test_electronic_consent import register, registration_payload, signature_data_url


def test_typed_signature_payload_generates_png_from_names():
    payload = {
        "participant_printed_name": "Alex Student",
        "guardian_printed_name": "Jordan Parent",
        "participant_signature_agreed": True,
        "guardian_signature_agreed": True,
        "participant_acknowledged": True,
        "guardian_acknowledged": True,
    }
    participant_png, guardian_png, method, _, _, p_text, g_text = _resolve_signature_payload(payload)
    assert method == "typed"
    assert p_text == "Alex Student"
    assert g_text == "Jordan Parent"
    assert participant_png.startswith("data:image/png;base64,")
    assert guardian_png.startswith("data:image/png;base64,")


def test_legacy_drawn_signatures_still_resolve():
    payload = {
        "participant_printed_name": "Legacy Student",
        "guardian_printed_name": "Legacy Parent",
        "participant_acknowledged": True,
        "guardian_acknowledged": True,
        "participant_signature_png": signature_data_url(),
        "guardian_signature_png": signature_data_url(),
    }
    _, _, method, _, _, _, _ = _resolve_signature_payload(payload)
    assert method == "drawn_legacy"


def test_new_registration_rejects_drawn_png(client, db: Session):
    payload = registration_payload()
    payload["participant_signature_png"] = signature_data_url()
    payload["guardian_signature_png"] = signature_data_url()
    payload.pop("participant_signature_agreed", None)
    payload.pop("guardian_signature_agreed", None)
    response = register(client, payload)
    assert response.status_code == 422


def test_synthetic_pdf_contains_banner():
    prefix = "data:image/png;base64,"
    name_png = prefix + base64.b64encode(typed_signature_png_bytes("Demo Student")).decode("ascii")
    guardian_png = prefix + base64.b64encode(typed_signature_png_bytes("Demo Guardian")).decode("ascii")
    pdf_bytes, _ = generate_consent_pdf(
        participant_printed_name="Demo Student",
        guardian_printed_name="Demo Guardian",
        participant_signature_png=name_png,
        guardian_signature_png=guardian_png,
        participant_signed_at=datetime.now(UTC),
        guardian_signed_at=datetime.now(UTC),
        is_synthetic_demo_record=True,
    )
    assert _pdf_contains_synthetic_marker(pdf_bytes)


def test_non_synthetic_pdf_does_not_add_banner():
    prefix = "data:image/png;base64,"
    name_png = prefix + base64.b64encode(typed_signature_png_bytes("Real Student")).decode("ascii")
    guardian_png = prefix + base64.b64encode(typed_signature_png_bytes("Real Guardian")).decode("ascii")
    pdf_bytes, sha = generate_consent_pdf(
        participant_printed_name="Real Student",
        guardian_printed_name="Real Guardian",
        participant_signature_png=name_png,
        guardian_signature_png=guardian_png,
        participant_signed_at=datetime(2024, 1, 2, tzinfo=UTC),
        guardian_signed_at=datetime(2024, 1, 2, tzinfo=UTC),
        is_synthetic_demo_record=False,
    )
    assert not _pdf_contains_synthetic_marker(pdf_bytes)
    pdf_again, sha_again = generate_consent_pdf(
        participant_printed_name="Real Student",
        guardian_printed_name="Real Guardian",
        participant_signature_png=name_png,
        guardian_signature_png=guardian_png,
        participant_signed_at=datetime(2024, 1, 2, tzinfo=UTC),
        guardian_signed_at=datetime(2024, 1, 2, tzinfo=UTC),
        is_synthetic_demo_record=False,
    )
    assert pdf_again == pdf_bytes
    assert sha_again == sha


def test_typed_signature_requires_agreement():
    payload = {
        "participant_printed_name": "Alex Student",
        "guardian_printed_name": "Jordan Parent",
        "participant_signature_agreed": False,
        "guardian_signature_agreed": True,
        "participant_acknowledged": True,
        "guardian_acknowledged": True,
    }
    with pytest.raises(ConsentError):
        _resolve_signature_payload(payload)
