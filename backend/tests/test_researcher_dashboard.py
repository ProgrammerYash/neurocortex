from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.daily_session import DailySession
from app.models.module_result import ModuleResult
from app.models.participant import Participant
from app.models.researcher import Researcher
from app.services.consent_service import record_withdrawal
from app.services.procedure_service import recompute_session_completion, resolve_active_procedure
from app.utils.security import create_access_token, create_researcher_access_token, hash_pin
from tests.test_electronic_consent import register, registration_payload


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


@pytest.fixture()
def researcher(db: Session) -> Researcher:
    researcher = Researcher(display_name="Dashboard Tester", email=f"{uuid4()}@example.test")
    db.add(researcher)
    db.commit()
    return researcher


def researcher_headers(researcher: Researcher) -> dict[str, str]:
    return {
        "Authorization": "Bearer "
        + create_researcher_access_token(
            researcher_id=researcher.id,
            display_name=researcher.display_name,
        )
    }


def participant_by_public_id(db: Session, public_id: str) -> Participant:
    return db.execute(select(Participant).where(Participant.public_id == public_id)).scalar_one()


def add_session(
    db: Session,
    participant: Participant,
    session_date: date,
    modules: dict[str, dict],
    *,
    session_slot: int = 0,
) -> DailySession:
    session = DailySession(
        participant_id=participant.id,
        session_date=session_date,
        session_slot=session_slot,
        status="in_progress",
        complete=False,
        started_at=datetime.now(UTC),
    )
    db.add(session)
    db.flush()
    for module_key, payload in modules.items():
        db.add(
            ModuleResult(
                session_id=session.id,
                module_key=module_key,
                payload=payload,
                recorded_at=datetime.combine(session_date, datetime.min.time(), tzinfo=UTC),
            )
        )
    db.flush()
    db.refresh(session, attribute_names=["module_results"])
    procedure = resolve_active_procedure(db)
    recompute_session_completion(session, procedure)
    db.flush()
    return session


CORE = {
    "reaction": {"avg": 250, "median": 240, "sd": 20, "min": 200, "max": 300, "missed": 0, "trials": 20},
    "typing": {"wpm": 42, "errorRate": 0.05, "backspaces": 1, "totalKeys": 120},
    "memory": {"accuracy": 85.5, "correct": 17, "total": 20},
    "attention": {"accuracy": 90, "avgRT": 420, "errors": 2},
    "survey": {"stress": 6, "fatigue": 7, "sleep": 7.5, "motivation": 5, "mood": 6},
}


def test_researcher_can_load_dashboard_summary_and_participants(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    registered = register(client, registration_payload())
    assert registered.status_code == 201, registered.text
    participant = participant_by_public_id(db, registered.json()["public_id"])
    add_session(db, participant, date(2026, 7, 10), CORE)
    db.commit()

    headers = researcher_headers(researcher)
    summary = client.get("/v1/research/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["totalParticipants"] >= 1
    assert body["totalSessions"] >= 1

    listing = client.get("/v1/research/dashboard/participants", headers=headers)
    assert listing.status_code == 200
    page = listing.json()
    assert page["total"] >= 1
    row = next(item for item in page["items"] if item["participantId"] == participant.public_id)
    assert row["studentName"] == "Test Student"
    assert row["guardianName"] == "Test Guardian"
    assert row["sessions"] == 1
    assert row["sessionCompletion"] == 100.0
    assert row["averageReactionTimeMs"] == 250
    assert row["averageStress"] == 6.0
    assert row["averageFatigue"] == 7.0
    assert row["averageSleepHours"] == 7.5
    assert row["averageMemoryAccuracy"] == 85.5
    assert "pdf_bytes" not in listing.text.lower()
    assert "signature_png" not in listing.text.lower()


def test_participant_token_receives_403(client: TestClient, db: Session):
    participant = Participant(
        public_id=f"NC-DASH-{uuid4().hex[:6].upper()}",
        pin_hash=hash_pin("1234"),
        grade="10th Grade",
        age_range="15-16",
        age_consent_category="under_18",
        pet_choice="fox",
    )
    db.add(participant)
    db.commit()
    headers = {
        "Authorization": "Bearer "
        + create_access_token(participant_id=participant.id, public_id=participant.public_id)
    }
    assert client.get("/v1/research/dashboard/summary", headers=headers).status_code == 403
    assert client.get("/v1/research/dashboard/participants", headers=headers).status_code == 403


def test_legacy_participant_without_consent_record_shows_dashes(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant = Participant(
        public_id=f"NC-LEG-{uuid4().hex[:6].upper()}",
        pin_hash=hash_pin("1234"),
        grade="11th Grade",
        age_range="15-16",
        age_consent_category="under_18",
        pet_choice="owl",
    )
    db.add(participant)
    db.commit()
    response = client.get(
        "/v1/research/dashboard/participants",
        headers=researcher_headers(researcher),
    )
    row = next(item for item in response.json()["items"] if item["participantId"] == participant.public_id)
    assert row["studentName"] is None
    assert row["guardianName"] is None


def test_session_count_uses_distinct_study_dates(client: TestClient, db: Session, researcher: Researcher):
    registered = register(client, registration_payload(idempotency_key=str(uuid4())))
    participant = participant_by_public_id(db, registered.json()["public_id"])
    add_session(db, participant, date(2026, 7, 1), {"reaction": CORE["reaction"]})
    add_session(db, participant, date(2026, 7, 2), {"memory": CORE["memory"]})
    db.commit()
    response = client.get(
        "/v1/research/dashboard/participants",
        headers=researcher_headers(researcher),
    )
    row = next(item for item in response.json()["items"] if item["participantId"] == participant.public_id)
    assert row["sessions"] == 2


def test_session_completion_uses_completed_over_started_dates(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    registered = register(client, registration_payload(idempotency_key=str(uuid4())))
    participant = participant_by_public_id(db, registered.json()["public_id"])
    add_session(db, participant, date(2026, 7, 3), CORE)
    add_session(db, participant, date(2026, 7, 4), {"reaction": CORE["reaction"]})
    db.commit()
    response = client.get(
        "/v1/research/dashboard/participants",
        headers=researcher_headers(researcher),
    )
    row = next(item for item in response.json()["items"] if item["participantId"] == participant.public_id)
    assert row["sessionCompletion"] == 50.0


def test_module_order_does_not_affect_completion(client: TestClient, db: Session, researcher: Researcher):
    registered = register(client, registration_payload(idempotency_key=str(uuid4())))
    participant = participant_by_public_id(db, registered.json()["public_id"])
    add_session(
        db,
        participant,
        date(2026, 7, 5),
        {
            "survey": CORE["survey"],
            "attention": CORE["attention"],
            "memory": CORE["memory"],
            "typing": CORE["typing"],
            "reaction": CORE["reaction"],
        },
    )
    db.commit()
    response = client.get(
        f"/v1/research/dashboard/participants/{participant.public_id}",
        headers=researcher_headers(researcher),
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["sessionsCompleted"] == 1
    assert detail["recentSessions"][0]["complete"] is True


def test_average_reaction_time_excludes_invalid_values(client: TestClient, db: Session, researcher: Researcher):
    registered = register(client, registration_payload(idempotency_key=str(uuid4())))
    participant = participant_by_public_id(db, registered.json()["public_id"])
    add_session(db, participant, date(2026, 7, 6), {"reaction": {"avg": 0, "missed": 20, "trials": 20}})
    add_session(db, participant, date(2026, 7, 7), {"reaction": {"avg": 300, "missed": 0, "trials": 20}})
    db.commit()
    response = client.get(
        "/v1/research/dashboard/participants",
        headers=researcher_headers(researcher),
    )
    row = next(item for item in response.json()["items"] if item["participantId"] == participant.public_id)
    assert row["averageReactionTimeMs"] == 300


def test_search_sort_and_pagination(client: TestClient, db: Session, researcher: Researcher):
    first = register(
        client,
        registration_payload(
            idempotency_key=str(uuid4()),
            participant_printed_name="Alpha Student",
            guardian_printed_name="Alpha Guardian",
        ),
    )
    second = register(
        client,
        registration_payload(
            idempotency_key=str(uuid4()),
            participant_printed_name="Beta Student",
            guardian_printed_name="Beta Guardian",
        ),
    )
    assert first.status_code == 201 and second.status_code == 201
    headers = researcher_headers(researcher)

    by_student = client.get("/v1/research/dashboard/participants?search=Alpha%20Student", headers=headers)
    assert by_student.json()["total"] == 1
    assert by_student.json()["items"][0]["studentName"] == "Alpha Student"

    by_guardian = client.get("/v1/research/dashboard/participants?search=Beta%20Guardian", headers=headers)
    assert by_guardian.json()["total"] == 1

    by_id = client.get(
        f"/v1/research/dashboard/participants?search={first.json()['public_id']}",
        headers=headers,
    )
    assert by_id.json()["total"] == 1

    page = client.get(
        "/v1/research/dashboard/participants?limit=1&offset=0&sort=participant_id&direction=asc",
        headers=headers,
    )
    assert page.status_code == 200
    assert len(page.json()["items"]) == 1
    assert page.json()["total"] >= 2


def test_withdrawn_status_and_detail_history(client: TestClient, db: Session, researcher: Researcher):
    registered = register(client, registration_payload(idempotency_key=str(uuid4())))
    participant = participant_by_public_id(db, registered.json()["public_id"])
    add_session(db, participant, date(2026, 7, 8), CORE)
    record_withdrawal(db, participant=participant)
    db.commit()
    headers = researcher_headers(researcher)
    row = next(
        item
        for item in client.get("/v1/research/dashboard/participants", headers=headers).json()["items"]
        if item["participantId"] == participant.public_id
    )
    assert row["status"] == "Withdrawn"
    detail = client.get(f"/v1/research/dashboard/participants/{participant.public_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["recentSessions"][0]["reactionCompleted"] is True
    assert "pdfBytes" not in detail.text
    assert "pin_hash" not in detail.text
