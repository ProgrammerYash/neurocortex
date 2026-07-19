"""Phase 3C.2 stabilization verification."""

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
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.participant import Participant
from app.services.consent_service import SESSION_BLOCK_MESSAGES, build_consent_status, session_block_message
from app.utils.security import hash_pin

client = TestClient(app)


def researcher_headers():
    response = client.post("/v1/auth/researcher/login", json={"invite_code": "YASH GUPTA"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def register_participant(**extra):
    body = {
        "grade": "10th Grade",
        "age_range": extra.pop("age_range", "17-18"),
        "pet_choice": "fox",
        "pin": extra.pop("pin", "5678"),
        **extra,
    }
    response = client.post("/v1/auth/participant/register", json=body)
    return response


def main():
    db = SessionLocal()
    try:
        unresolved = Participant(
            public_id=f"NC-UNR{uuid4().hex[:6].upper()}",
            pin_hash=hash_pin("1212"),
            grade="11th Grade",
            age_range="17-18",
            age_consent_category="unresolved",
            pet_choice="fox",
        )
        db.add(unresolved)
        db.commit()
        db.refresh(unresolved)
        public_id = unresolved.public_id
    finally:
        db.close()

    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": public_id, "pin": "1212"},
    )
    assert login.status_code == 200, login.text
    participant_token = login.json()["access_token"]

    blocked = client.post(
        f"/v1/research/participants/{public_id}/resolve-age-category",
        headers={"Authorization": f"Bearer {participant_token}"},
        json={"age_consent_category": "under_18"},
    )
    assert blocked.status_code == 403
    print("participant cannot resolve age category OK")

    researcher = researcher_headers()
    before_audit = db = SessionLocal()
    try:
        before_count = before_audit.execute(select(AuditEvent)).scalars().all()
        before_len = len(before_count)
    finally:
        before_audit.close()

    resolved = client.post(
        f"/v1/research/participants/{public_id}/resolve-age-category",
        headers=researcher,
        json={"age_consent_category": "under_18"},
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["age_consent_category"] == "under_18"
    print("researcher can resolve age category OK")

    db = SessionLocal()
    try:
        after_events = db.execute(
            select(AuditEvent).where(AuditEvent.event_type == "age_consent_category_resolved")
        ).scalars().all()
        assert any(event.metadata_json.get("resolved_to") == "under_18" for event in after_events)
        print("audit event created OK")
    finally:
        db.close()

    status = client.get(
        "/v1/participants/me/consent-status",
        headers={"Authorization": f"Bearer {participant_token}"},
    ).json()
    assert status["session_block_reason"] == "CONSENT_REQUIRED"
    assert status["session_block_message"] == SESSION_BLOCK_MESSAGES["CONSENT_REQUIRED"]
    print("unresolved age now blocks with consent message OK")

    db = SessionLocal()
    try:
        blocked_participant = Participant(
            public_id=f"NC-BLK{uuid4().hex[:6].upper()}",
            pin_hash=hash_pin("3434"),
            grade="10th Grade",
            age_range="17-18",
            age_consent_category="unresolved",
            pet_choice="fox",
        )
        db.add(blocked_participant)
        db.commit()
        db.refresh(blocked_participant)
        blocked_status = build_consent_status(db, blocked_participant)
        assert blocked_status["session_eligible"] is False
        assert blocked_status["session_block_reason"] == "AGE_CONSENT_CATEGORY_REQUIRED"
        assert blocked_status["session_block_message"] == session_block_message("AGE_CONSENT_CATEGORY_REQUIRED")
    finally:
        db.close()
    print("unresolved age blocks sessions OK")

    session_attempt = client.put(
        f"/v1/participants/me/sessions/{date.today().isoformat()}/modules/reaction",
        headers={"Authorization": f"Bearer {participant_token}"},
        json={"payload": {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20}},
    )
    assert session_attempt.status_code == 403
    assert session_attempt.json()["detail"]["error_code"] == "CONSENT_REQUIRED"
    assert session_attempt.json()["detail"]["message"] == SESSION_BLOCK_MESSAGES["CONSENT_REQUIRED"]
    print("session API returns clear blocking reason OK")

    report = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "study_readiness_report.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert report.returncode == 0, report.stdout + report.stderr
    assert "NeuroCortex Study Readiness Report" in report.stdout
    print("study readiness report OK")

    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "test_phase3b.py")])
    print("Phase 3B regression OK")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "test_phase3c.py")])
    print("Phase 3C regression OK")
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "test_phase3c1.py")])
    print("Phase 3C.1 regression OK")
    print("ALL PHASE 3C.2 TESTS PASSED")


if __name__ == "__main__":
    main()
