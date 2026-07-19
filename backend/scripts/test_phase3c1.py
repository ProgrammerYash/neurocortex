"""Phase 3C.1 official Form 4 integration and consent corrections."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["REQUIRE_CONSENT_FOR_SESSIONS"] = "true"
os.environ["ACTIVE_STUDY_PROTOCOL_VERSION"] = "2026-pilot-v1"
os.environ["ALLOW_RESEARCHER_CONSENT_OVERRIDE"] = "true"
os.environ["STUDY_MODE"] = "pilot"

from app.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.participant import Participant
from app.models.participant_consent_event import ParticipantConsentEvent
from app.services.consent_service import (
    build_consent_status,
    get_age_category,
    is_ml_eligible,
    record_participant_consent,
    resolve_consent_category,
)
from app.services.document_service import DocumentError, resolve_download_path
from app.services.pdf_form_service import (
    OFFICIAL_TEMPLATE_SHA256,
    TEMPLATE_PDF,
    compute_template_sha256,
    load_template_metadata,
)
from app.services.session_service import SessionError, upsert_module_result
from app.utils.security import hash_pin

client = TestClient(app)
OFFICIAL_SHA256 = OFFICIAL_TEMPLATE_SHA256.lower()


def register_via_api(**extra):
    body = {
        "grade": "10th Grade",
        "age_range": extra.pop("age_range", "15-16"),
        "pet_choice": "fox",
        "pin": extra.pop("pin", "5678"),
        **extra,
    }
    response = client.post("/v1/auth/participant/register", json=body)
    return response


def researcher_headers():
    response = client.post("/v1/auth/researcher/login", json={"invite_code": "YASH GUPTA"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def main():
    metadata = load_template_metadata()
    assert TEMPLATE_PDF.exists(), "Official template must exist"
    actual_hash = compute_template_sha256().lower()
    assert actual_hash == OFFICIAL_SHA256, actual_hash
    assert metadata["sha256"].lower() == OFFICIAL_SHA256
    print("official template OK", actual_hash[:16])

    from scripts.create_form4_template import create_template

    try:
        create_template(force=True)
        raise AssertionError("Placeholder script must refuse to overwrite official template")
    except RuntimeError:
        print("placeholder overwrite blocked OK")

    db = SessionLocal()
    try:
        legacy = Participant(
            public_id=f"NC-LGY{uuid4().hex[:6].upper()}",
            pin_hash=hash_pin("9090"),
            grade="11th Grade",
            age_range="17-18",
            age_consent_category="unresolved",
            pet_choice="fox",
        )
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        assert resolve_consent_category(legacy) == "unresolved"
        status = build_consent_status(db, legacy)
        assert status["session_eligible"] is False
        assert status["session_block_reason"] == "AGE_CONSENT_CATEGORY_REQUIRED"
        print("legacy 17-18 unresolved OK")
    finally:
        db.close()

    minor = register_via_api(
        age_range="15-16",
        pin="1111",
        assent_acknowledged=True,
        parental_permission_status="pending",
    )
    assert minor.status_code in {200, 201}
    minor_token = minor.json()["access_token"]
    status = client.get("/v1/participants/me/consent-status", headers={"Authorization": f"Bearer {minor_token}"})
    assert status.json()["session_eligible"] is False
    assert status.json()["parental_permission_status"] == "pending"

    response = client.put(
        f"/v1/participants/me/sessions/{date.today().isoformat()}/modules/reaction",
        headers={"Authorization": f"Bearer {minor_token}"},
        json={"payload": {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20}},
    )
    assert response.status_code == 403
    print("minor pending parental blocks sessions OK")

    denied = register_via_api(
        age_range="15-16",
        pin="1122",
        assent_acknowledged=True,
        parental_permission_status="granted",
    )
    assert denied.status_code == 422
    print("participant cannot mark parental granted OK")

    ambiguous = register_via_api(age_range="17-18", pin="1133")
    assert ambiguous.status_code == 422
    print("17-18 requires age_consent_category OK")

    adult = register_via_api(
        age_range="17-18",
        pin="1144",
        age_consent_category="age_18_or_over",
        adult_consent_acknowledged=True,
    )
    assert adult.status_code in {200, 201}
    adult_token = adult.json()["access_token"]
    assert client.get("/v1/participants/me/consent-status", headers={"Authorization": f"Bearer {adult_token}"}).json()["session_eligible"] is True
    print("adult workflow OK")

    researcher = researcher_headers()
    public_id = minor.json()["public_id"]
    verify = client.post(
        f"/v1/research/participants/{public_id}/consent-event",
        headers=researcher,
        json={
            "event_type": "parental_permission_granted",
            "status": "granted",
            "form_type": "parental_permission",
        },
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["parental_permission_status"] == "granted"
    session_save = client.put(
        f"/v1/participants/me/sessions/{date.today().isoformat()}/modules/reaction",
        headers={"Authorization": f"Bearer {minor_token}"},
        json={"payload": {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20}},
    )
    assert session_save.status_code == 200, session_save.text
    print("researcher parental verification OK")

    os.environ["ALLOW_RESEARCHER_CONSENT_OVERRIDE"] = "false"
    get_settings.cache_clear()
    blocked = client.post(
        f"/v1/research/participants/{public_id}/consent-event",
        headers=researcher,
        json={"event_type": "assent_granted", "status": "granted", "form_type": "participant_assent"},
    )
    assert blocked.status_code == 403
    os.environ["ALLOW_RESEARCHER_CONSENT_OVERRIDE"] = "true"
    get_settings.cache_clear()
    print("researcher override flag enforced OK")

    draft = client.post(
        "/v1/research/documents/form-4/draft",
        headers=researcher,
        json={"project_title": "Phase 3C.1 Verification Study"},
    )
    assert draft.status_code in {200, 201}, draft.text
    doc_id = draft.json()["id"]
    assert draft.json()["template_id"]
    assert draft.json()["has_generated_pdf"] is False
    assert "artifact_path" not in draft.json()

    updated = client.put(
        f"/v1/research/documents/form-4/{doc_id}",
        headers=researcher,
        json={
            "student_researcher_names": "Student Researcher",
            "project_title": "Phase 3C.1 Verification Study",
            "adult_sponsor": "Adult Sponsor",
            "adult_sponsor_contact": "555-0100",
            "research_plan_submitted": True,
            "full_committee_review": True,
            "risk_level": "minimal",
            "qualified_scientist_required": False,
            "risk_assessment_required": False,
            "minor_assent_required": "yes",
            "parental_permission_required": "yes",
            "adult_informed_consent_required": "not_applicable",
        },
    )
    assert updated.status_code == 200

    generated = client.post(f"/v1/research/documents/form-4/{doc_id}/generate", headers=researcher)
    assert generated.status_code == 200, generated.text
    assert generated.json()["status"] == "awaiting_irb"
    assert len(generated.json()["artifact_hash"]) == 64
    pdf_bytes = client.get(f"/v1/research/documents/{doc_id}/download", headers=researcher).content
    assert pdf_bytes.startswith(b"%PDF")
    assert pdf_bytes.startswith(b"%PDF")
    print("official PDF generation OK")

    participant_doc = client.get(f"/v1/research/documents/{doc_id}", headers={"Authorization": f"Bearer {minor_token}"})
    assert participant_doc.status_code == 403
    unauth = client.get(f"/v1/research/documents/{doc_id}/download")
    assert unauth.status_code == 401
    print("document access controls OK")

    invalid_status = client.put(
        f"/v1/research/documents/form-4/{doc_id}/status",
        headers=researcher,
        json={"status": "approved", "confirm_approved": False},
    )
    assert invalid_status.status_code == 422

    invalid_transition = client.put(
        f"/v1/research/documents/form-4/{doc_id}/status",
        headers=researcher,
        json={"status": "approved", "confirm_approved": True},
    )
    assert invalid_transition.status_code == 422
    print("document status validation OK")

    db = SessionLocal()
    try:
        from app.models.generated_study_document import GeneratedStudyDocument

        document = db.get(GeneratedStudyDocument, doc_id)
        document.artifact_path = "../../../templates/4-Human-Participants.pdf"
        db.commit()
        try:
            resolve_download_path(db, doc_id)
            raise AssertionError("Expected path traversal block")
        except DocumentError as exc:
            assert exc.error_code in {"PATH_TRAVERSAL", "PATH_FORBIDDEN", "INVALID_DOCUMENT_PATH", "PATH_TRAVERSAL"}
        audit_count = db.execute(select(func.count()).select_from(AuditEvent)).scalar_one()
        assert audit_count >= 5
        print("path traversal blocked OK", "audit events", audit_count)
    finally:
        db.close()

    verify_script = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_form4_layout.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert verify_script.returncode == 0, verify_script.stdout + verify_script.stderr
    print("visual verification files OK")

    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "test_phase3c.py")])
    print("Phase 3C regression OK")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "test_phase3b.py")])
    print("Phase 3B regression OK")
    print("ALL PHASE 3C.1 TESTS PASSED")


if __name__ == "__main__":
    main()
