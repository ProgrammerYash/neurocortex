"""Phase 3D study launch readiness and data collection preparation verification."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["REQUIRE_CONSENT_FOR_SESSIONS"] = "true"
os.environ["ACTIVE_STUDY_PROTOCOL_VERSION"] = "2026-pilot-v1"
os.environ["ACTIVE_STUDY_PROCEDURE_VERSION"] = "2026-pilot-procedure-v1"
os.environ["ALLOW_RESEARCHER_CONSENT_OVERRIDE"] = "true"
os.environ["STUDY_MODE"] = "pilot"

from app.config import get_settings

get_settings.cache_clear()

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.daily_session import SESSION_STATUS_ABANDONED, SESSION_STATUS_COMPLETE, DailySession
from app.models.participant import Participant
from app.models.session_data_quality_flag import SessionDataQualityFlag
from app.services.consent_service import record_participant_consent, record_researcher_consent_event, record_withdrawal
from app.services.data_quality_service import validate_session_data_quality
from app.services.procedure_service import resolve_active_procedure
from app.services.research_etl import _evaluate_session_dataset_eligibility, build_research_dataset
from app.services.session_service import SessionError, upsert_module_result
from app.utils.security import hash_pin

client = TestClient(app)

REACTION = {"avg": 300, "median": 290, "sd": 20, "min": 200, "max": 400, "missed": 0, "trials": 20}
TYPING = {
    "wpm": 40,
    "errorRate": 0.05,
    "backspaces": 1,
    "avgInterval": 100,
    "variance": 10,
    "avgDwell": 70,
    "burstLength": 4,
    "pauseFrequency": 0.2,
    "totalKeys": 100,
    "errCorrectionRate": 0.1,
}
MEMORY = {"accuracy": 80, "responseTime": 1200, "distractionScore": 0.2}
ATTENTION = {"accuracy": 90, "avgRT": 450, "errors": 1, "congruentAcc": 95, "incongruentAcc": 85}
SURVEY = {
    "stress": 4,
    "fatigue": 3,
    "motivation": 7,
    "mood": 6,
    "sleep": 7,
    "study": 5,
    "homework": 4,
    "exam": False,
    "socialStress": 2,
    "physicalActivity": 6,
}


def researcher_headers():
    response = client.post("/v1/auth/researcher/login", json={"invite_code": "YASH GUPTA"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_consented_participant(db) -> Participant:
    participant = Participant(
        public_id=f"NC-P3D{uuid4().hex[:6].upper()}",
        pin_hash=hash_pin("9090"),
        grade="10th Grade",
        age_range="15-16",
        age_consent_category="under_18",
        pet_choice="fox",
    )
    db.add(participant)
    db.commit()
    db.refresh(participant)
    record_participant_consent(
        db,
        participant=participant,
        payload={"assent_acknowledged": True, "parental_permission_status": "pending"},
    )
    from app.models.researcher import Researcher

    researcher = db.execute(select(Researcher).limit(1)).scalar_one()
    record_researcher_consent_event(
        db,
        participant=participant,
        researcher_id=researcher.id,
        payload={
            "event_type": "parental_permission_granted",
            "status": "granted",
            "form_type": "parental_permission",
        },
    )
    db.refresh(participant)
    return participant


def complete_session(db, participant: Participant, session_date: date) -> dict:
    upsert_module_result(db, participant, session_date, "reaction", REACTION)
    upsert_module_result(db, participant, session_date, "typing", TYPING)
    upsert_module_result(db, participant, session_date, "memory", MEMORY)
    upsert_module_result(db, participant, session_date, "attention", ATTENTION)
    session = db.execute(
        select(DailySession).where(
            DailySession.participant_id == participant.id,
            DailySession.session_date == session_date,
        )
    ).scalar_one()
    session.started_at = datetime.now(UTC) - timedelta(minutes=3)
    db.commit()
    return upsert_module_result(db, participant, session_date, "survey", SURVEY)


def main():
    db = SessionLocal()
    try:
        procedure = resolve_active_procedure(db)
        assert procedure.version == "2026-pilot-procedure-v1"
        assert procedure.required_modules[0] == "reaction"
        print("active study procedure OK")

        participant = create_consented_participant(db)
        today = date.today()

        try:
            upsert_module_result(db, participant, today, "typing", TYPING)
            raise AssertionError("Expected module order violation")
        except SessionError as exc:
            assert exc.error_code == "MODULE_ORDER_VIOLATION"
        print("module order enforcement OK")

        saved = upsert_module_result(db, participant, today, "reaction", REACTION)
        assert saved["status"] == "in_progress"
        print("incomplete session status OK")

        try:
            upsert_module_result(db, participant, today, "memory", MEMORY)
            raise AssertionError("Expected module skip/order violation")
        except SessionError as exc:
            assert exc.error_code == "MODULE_ORDER_VIOLATION"
        print("required modules cannot be skipped OK")

        complete_session(db, participant, today)
        session = db.execute(
            select(DailySession).where(
                DailySession.participant_id == participant.id,
                DailySession.session_date == today,
            )
        ).scalar_one()
        assert session.status == SESSION_STATUS_COMPLETE
        print("completed session status OK")

        try:
            upsert_module_result(
                db,
                participant,
                today,
                "reaction",
                REACTION,
            )
            raise AssertionError("Expected daily session limit")
        except SessionError as exc:
            assert exc.error_code in {"DAILY_SESSION_LIMIT_REACHED", "SESSION_ALREADY_COMPLETE"}
        print("daily session limit OK")

        interval_participant = create_consented_participant(db)
        recent = DailySession(
            participant_id=interval_participant.id,
            session_date=today - timedelta(days=1),
            session_slot=0,
            status=SESSION_STATUS_COMPLETE,
            complete=True,
            started_at=datetime.now(UTC) - timedelta(minutes=90),
            completed_at=datetime.now(UTC) - timedelta(minutes=30),
            procedure_version=procedure.version,
        )
        db.add(recent)
        db.commit()
        try:
            upsert_module_result(db, interval_participant, today, "reaction", REACTION)
            raise AssertionError("Expected session interval block")
        except SessionError as exc:
            assert exc.error_code == "SESSION_INTERVAL_TOO_SOON"
        print("minimum interval enforcement OK")

        abandon_participant = create_consented_participant(db)
        upsert_module_result(db, abandon_participant, today, "reaction", REACTION)
        login = client.post(
            "/v1/auth/participant/login",
            json={"public_id": abandon_participant.public_id, "pin": "9090"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        abandoned = client.post(
            f"/v1/participants/me/sessions/{today.isoformat()}/abandon",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert abandoned.status_code == 200, abandoned.text
        assert abandoned.json()["status"] == SESSION_STATUS_ABANDONED
        print("abandoned session behavior OK")

        dq_participant = create_consented_participant(db)
        upsert_module_result(
            db,
            dq_participant,
            today,
            "reaction",
            {**REACTION, "min": 50, "avg": 50},
        )
        session = db.execute(
            select(DailySession).where(
                DailySession.participant_id == dq_participant.id,
                DailySession.session_date == today,
            )
        ).scalar_one()
        flags = db.execute(
            select(SessionDataQualityFlag).where(SessionDataQualityFlag.session_id == session.id)
        ).scalars().all()
        assert any(flag.flag_type == "impossible_reaction_time" for flag in flags)
        flag = next(item for item in flags if item.flag_type == "impossible_reaction_time")
        print("data-quality flag creation OK")

        researcher = researcher_headers()
        participant_review = client.post(
            f"/v1/research/data-quality/flags/{flag.id}/review",
            headers={"Authorization": f"Bearer {token}"},
            json={"review_status": "reviewed_valid"},
        )
        assert participant_review.status_code == 403
        reviewed = client.post(
            f"/v1/research/data-quality/flags/{flag.id}/review",
            headers=researcher,
            json={"review_status": "reviewed_valid"},
        )
        assert reviewed.status_code == 200, reviewed.text
        db2 = SessionLocal()
        try:
            audit = db2.execute(
                select(AuditEvent).where(AuditEvent.event_type == "data_quality_flag_reviewed")
            ).scalars().all()
            assert any(item.metadata_json.get("flag_id") == str(flag.id) for item in audit)
        finally:
            db2.close()
        print("researcher flag review permissions and audit OK")

        progress_participant = create_consented_participant(db)
        complete_session(db, progress_participant, today)
        progress_login = client.post(
            "/v1/auth/participant/login",
            json={"public_id": progress_participant.public_id, "pin": "9090"},
        ).json()
        progress = client.get(
            "/v1/participants/me/study-progress",
            headers={"Authorization": f"Bearer {progress_login['access_token']}"},
        )
        assert progress.status_code == 200, progress.text
        body = progress.json()
        assert body["completed_sessions"] >= 1
        assert body["required_sessions"] == procedure.min_sessions_per_participant
        assert body["today_session_complete"] is True
        assert "session_block" not in str(body).lower() or body["session_can_start"] is False
        print("participant progress calculations OK")

        dataset_participant = create_consented_participant(db)
        complete_session(db, dataset_participant, today)
        session = db.execute(
            select(DailySession).where(
                DailySession.participant_id == dataset_participant.id,
                DailySession.session_date == today,
            )
        ).scalar_one()
        eligible, reasons, warnings = _evaluate_session_dataset_eligibility(
            db,
            participant=dataset_participant,
            session=session,
            dataset_mode="strict",
        )
        assert eligible, reasons
        strict = build_research_dataset(db, dataset_mode="strict", name="phase3d-strict")
        assert strict.row_count >= 1
        exploratory = build_research_dataset(db, dataset_mode="exploratory", name="phase3d-exploratory")
        assert exploratory.row_count >= strict.row_count
        print("strict and exploratory dataset builds OK")

        withdrawn_participant = create_consented_participant(db)
        complete_session(db, withdrawn_participant, today)
        session = db.execute(
            select(DailySession).where(
                DailySession.participant_id == withdrawn_participant.id,
                DailySession.session_date == today,
            )
        ).scalar_one()
        record_withdrawal(db, participant=withdrawn_participant)
        eligible, reasons, _ = _evaluate_session_dataset_eligibility(
            db,
            participant=withdrawn_participant,
            session=session,
            dataset_mode="strict",
        )
        assert eligible, f"Session completed before withdrawal should remain eligible: {reasons}"

        consent_timing_participant = create_consented_participant(db)
        complete_session(db, consent_timing_participant, today)
        session_old = db.execute(
            select(DailySession).where(
                DailySession.participant_id == consent_timing_participant.id,
                DailySession.session_date == today,
            )
        ).scalar_one()
        session_old.completed_at = datetime.now(UTC) - timedelta(days=5)
        db.commit()
        from app.services.consent_service import consent_eligible_at_session_time

        consent_ok, consent_reasons = consent_eligible_at_session_time(
            db, consent_timing_participant, session_old
        )
        assert consent_ok is False
        assert "CONSENT_NOT_ACTIVE_AT_SESSION_TIME" in consent_reasons or "PARENTAL_PERMISSION_NOT_ACTIVE_AT_SESSION_TIME" in consent_reasons
        eligible, reasons, _ = _evaluate_session_dataset_eligibility(
            db,
            participant=consent_timing_participant,
            session=session_old,
            dataset_mode="strict",
        )
        assert eligible is False
        assert any("CONSENT" in reason or "PARENTAL" in reason for reason in reasons)
        print("withdrawal and consent-at-session-time eligibility OK")

        dashboard = client.get("/v1/research/data-quality/dashboard", headers=researcher)
        assert dashboard.status_code == 200, dashboard.text
        assert "completed_sessions" in dashboard.json()
        procedure_view = client.get("/v1/research/study-procedure", headers=researcher)
        assert procedure_view.status_code == 200, procedure_view.text
        assert procedure_view.json()["version"] == "2026-pilot-procedure-v1"
        print("researcher data-quality dashboard and procedure view OK")
    finally:
        db.close()

    checklist = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "study_launch_checklist.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checklist.returncode == 0, checklist.stdout + checklist.stderr
    print("study launch checklist execution OK")

    print("Phase 3D tests passed.")


if __name__ == "__main__":
    main()
