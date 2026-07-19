"""Phase 3C consent, enrollment, and Form 4 verification."""

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

from app.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.generated_study_document import GeneratedStudyDocument
from app.models.participant import Participant
from app.models.participant_consent_event import ParticipantConsentEvent
from app.services.consent_service import (
    get_age_category,
    is_ml_eligible,
    record_participant_consent,
    record_withdrawal,
    required_consent_types,
    resolve_active_protocol,
    set_ml_exclusion,
)
from app.services.document_service import DocumentError, resolve_download_path
from app.services.session_service import SessionError, upsert_module_result
from app.utils.security import hash_pin

client = TestClient(app)


def register_via_api(**extra):
    body = {
        "grade": "10th Grade",
        "age_range": extra.pop("age_range", "15-16"),
        "pet_choice": "fox",
        "pin": extra.pop("pin", "5678"),
        **extra,
    }
    response = client.post("/v1/auth/participant/register", json=body)
    assert response.status_code in {200, 201}, response.text
    return response.json()


def researcher_headers():
    response = client.post("/v1/auth/researcher/login", json={"invite_code": "YASH GUPTA"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def verify_parental_permission(public_id: str, headers: dict) -> None:
    response = client.post(
        f"/v1/research/participants/{public_id}/consent-event",
        headers=headers,
        json={
            "event_type": "parental_permission_granted",
            "status": "granted",
            "form_type": "parental_permission",
        },
    )
    assert response.status_code == 200, response.text


def main():
    db = SessionLocal()
    try:
        protocol = resolve_active_protocol(db)
        assert protocol.version == "2026-pilot-v1"
        sample = Participant(
            public_id="TEMP",
            pin_hash="x",
            grade="10th Grade",
            age_range="15-16",
            age_consent_category="under_18",
            pet_choice="fox",
        )
        assert get_age_category(sample) == "minor"
        sample.age_consent_category = "age_18_or_over"
        sample.age_range = "23+"
        assert get_age_category(sample) == "adult"
        assert "participant_assent" in required_consent_types(
            Participant(public_id="T", pin_hash="x", grade="g", age_range="15-16", age_consent_category="under_18", pet_choice="fox")
        )
        print("active protocol OK", protocol.version)
    finally:
        db.close()

    db = SessionLocal()
    try:
        blocked = Participant(
            public_id=f"NC-BLK{uuid4().hex[:6].upper()}",
            pin_hash=hash_pin("8888"),
            grade="10th Grade",
            age_range="15-16",
            age_consent_category="under_18",
            pet_choice="fox",
        )
        db.add(blocked)
        db.commit()
        db.refresh(blocked)
        try:
            upsert_module_result(
                db,
                blocked,
                date.today(),
                "reaction",
                {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20},
            )
            raise AssertionError("Expected session to be blocked without consent")
        except SessionError as exc:
            assert exc.error_code in {"CONSENT_REQUIRED", "PARENTAL_PERMISSION_REQUIRED"}

        allowed = Participant(
            public_id=f"NC-ALW{uuid4().hex[:6].upper()}",
            pin_hash=hash_pin("7777"),
            grade="10th Grade",
            age_range="15-16",
            age_consent_category="under_18",
            pet_choice="fox",
        )
        db.add(allowed)
        db.commit()
        db.refresh(allowed)
        record_participant_consent(
            db,
            participant=allowed,
            payload={"assent_acknowledged": True, "parental_permission_status": "pending"},
        )
        from app.models.researcher import Researcher

        researcher = db.execute(select(Researcher).limit(1)).scalar_one()
        from app.services.consent_service import record_researcher_consent_event

        record_researcher_consent_event(
            db,
            participant=allowed,
            researcher_id=researcher.id,
            payload={
                "event_type": "parental_permission_granted",
                "status": "granted",
                "form_type": "parental_permission",
            },
        )
        saved = upsert_module_result(
            db,
            allowed,
            date.today(),
            "reaction",
            {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20},
        )
        assert saved["reaction"]
        record_withdrawal(db, participant=allowed)
        try:
            upsert_module_result(
                db,
                allowed,
                date.today(),
                "typing",
                {"wpm": 40, "errorRate": 0.05, "backspaces": 1, "avgInterval": 100, "variance": 10, "avgDwell": 70, "burstLength": 4, "pauseFrequency": 0.2, "totalKeys": 100, "errCorrectionRate": 0.1},
            )
            raise AssertionError("Expected withdrawn participant to be blocked")
        except SessionError as exc:
            assert exc.error_code == "PARTICIPANT_WITHDRAWN"
        print("session gating OK")
    finally:
        db.close()

    researcher = researcher_headers()
    minor_no_consent = register_via_api(age_range="15-16", pin="1111")
    status = client.get(
        "/v1/participants/me/consent-status",
        headers={"Authorization": f"Bearer {minor_no_consent['access_token']}"},
    ).json()
    assert status["session_eligible"] is False

    minor = register_via_api(
        age_range="15-16",
        pin="2222",
        assent_acknowledged=True,
        parental_permission_status="pending",
    )
    verify_parental_permission(minor["public_id"], researcher)
    status = client.get(
        "/v1/participants/me/consent-status",
        headers={"Authorization": f"Bearer {minor['access_token']}"},
    ).json()
    assert status["session_eligible"] is True

    withdrawn = client.post(
        "/v1/participants/me/withdraw",
        headers={"Authorization": f"Bearer {minor['access_token']}"},
    ).json()
    assert withdrawn["withdrawal_status"] == "withdrawn"
    blocked_session = client.put(
        f"/v1/participants/me/sessions/{date.today().isoformat()}/modules/reaction",
        headers={"Authorization": f"Bearer {minor['access_token']}"},
        json={"payload": {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20}},
    )
    assert blocked_session.status_code == 403
    print("withdrawal blocks sessions OK")

    adult = register_via_api(
        age_range="19-20",
        pin="3333",
        adult_consent_acknowledged=True,
    )
    adult_status = client.get(
        "/v1/participants/me/consent-status",
        headers={"Authorization": f"Bearer {adult['access_token']}"},
    ).json()
    assert adult_status["adult_consent_status"] == "granted"

    other = register_via_api(
        age_range="15-16",
        pin="4444",
        assent_acknowledged=True,
        parental_permission_status="pending",
    )
    assert client.get(
        f"/v1/research/participants/{other['public_id']}/consent-status",
        headers={"Authorization": f"Bearer {minor_no_consent['access_token']}"},
    ).status_code == 403

    db = SessionLocal()
    try:
        participant = db.execute(select(Participant).where(Participant.public_id == other["public_id"])).scalar_one()
        before = db.execute(
            select(func.count()).select_from(ParticipantConsentEvent).where(ParticipantConsentEvent.participant_id == participant.id)
        ).scalar_one()
        record_participant_consent(db, participant=participant, payload={"assent_acknowledged": True, "parental_permission_status": "pending"})
        after = db.execute(
            select(func.count()).select_from(ParticipantConsentEvent).where(ParticipantConsentEvent.participant_id == participant.id)
        ).scalar_one()
        assert after > before

        ml_participant = Participant(
            public_id=f"NC-ML{uuid4().hex[:6].upper()}",
            pin_hash=hash_pin("6666"),
            grade="10th Grade",
            age_range="15-16",
            age_consent_category="under_18",
            pet_choice="fox",
        )
        db.add(ml_participant)
        db.commit()
        db.refresh(ml_participant)
        record_participant_consent(db, participant=ml_participant, payload={"assent_acknowledged": True, "parental_permission_status": "pending"})
        from app.models.researcher import Researcher

        researcher_row = db.execute(select(Researcher).limit(1)).scalar_one()
        record_researcher_consent_event = __import__("app.services.consent_service", fromlist=["record_researcher_consent_event"]).record_researcher_consent_event
        record_researcher_consent_event(
            db,
            participant=ml_participant,
            researcher_id=researcher_row.id,
            payload={"event_type": "parental_permission_granted", "status": "granted", "form_type": "parental_permission"},
        )
        assert is_ml_eligible(db, ml_participant)[0] is True
        set_ml_exclusion(db, participant=ml_participant, researcher_id=researcher_row.id, excluded=True)
        assert is_ml_eligible(db, ml_participant) == (False, "EXCLUDED_FROM_ML")
        print("ML exclusion OK")
    finally:
        db.close()

    draft = client.post(
        "/v1/research/documents/form-4/draft",
        headers=researcher,
        json={"project_title": "NeuroCortex Test Study"},
    )
    assert draft.status_code in {200, 201}, draft.text
    doc_id = draft.json()["id"]
    client.put(
        f"/v1/research/documents/form-4/{doc_id}",
        headers=researcher,
        json={
            "student_researcher_names": "Student Researcher",
            "project_title": "NeuroCortex Test Study",
            "adult_sponsor": "Adult Sponsor",
            "research_plan_submitted": True,
            "risk_level": "minimal",
            "minor_assent_required": "yes",
            "parental_permission_required": "yes",
            "adult_informed_consent_required": "not_applicable",
        },
    )
    assert client.get(f"/v1/research/documents/{doc_id}", headers={"Authorization": f"Bearer {minor['access_token']}"}).status_code == 403
    generated = client.post(f"/v1/research/documents/form-4/{doc_id}/generate", headers=researcher)
    assert generated.status_code == 200
    assert len(generated.json()["artifact_hash"]) == 64
    pdf = client.get(f"/v1/research/documents/{doc_id}/download", headers=researcher)
    assert pdf.content.startswith(b"%PDF")

    db = SessionLocal()
    try:
        document = db.get(GeneratedStudyDocument, doc_id)
        document.artifact_path = "../../../etc/passwd"
        db.commit()
        try:
            resolve_download_path(db, doc_id)
            raise AssertionError("Expected path traversal to fail")
        except DocumentError:
            pass
        audit_count = db.execute(select(func.count()).select_from(AuditEvent)).scalar_one()
        assert audit_count >= 3
    finally:
        db.close()

    print("ALL PHASE 3C TESTS PASSED")


if __name__ == "__main__":
    main()
