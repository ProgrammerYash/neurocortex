from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.participant import Participant
from app.models.researcher import Researcher
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
    researcher = Researcher(display_name="Preference Tester", email=f"{uuid4()}@example.test")
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


def enrolled(client: TestClient, db: Session) -> Participant:
    response = register(client, registration_payload(idempotency_key=str(uuid4())))
    assert response.status_code == 201, response.text
    return db.execute(
        select(Participant).where(Participant.public_id == response.json()["public_id"])
    ).scalar_one()


def participant_headers(participant: Participant) -> dict[str, str]:
    token = create_access_token(
        participant_id=participant.id,
        public_id=participant.public_id,
        auth_version=participant.auth_version,
    )
    return {"Authorization": f"Bearer {token}"}


def test_participant_study_frequency_null_by_default(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    assert participant.study_frequency is None


@pytest.mark.parametrize(
    "value",
    ["daily", "twice_weekly", "four_times_weekly", "weekly"],
)
def test_participant_can_set_study_frequency(client: TestClient, db: Session, value: str) -> None:
    participant = enrolled(client, db)
    response = client.patch(
        "/v1/participants/me/preferences",
        headers=participant_headers(participant),
        json={"study_frequency": value},
    )
    assert response.status_code == 200, response.text
    assert response.json()["study_frequency"] == value
    db.refresh(participant)
    assert participant.study_frequency == value


def test_invalid_study_frequency_rejected(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    response = client.patch(
        "/v1/participants/me/preferences",
        headers=participant_headers(participant),
        json={"study_frequency": "every_day"},
    )
    assert response.status_code == 422


def test_preferences_require_authentication(client: TestClient) -> None:
    response = client.patch(
        "/v1/participants/me/preferences",
        json={"study_frequency": "daily"},
    )
    assert response.status_code == 401


def test_me_includes_study_frequency(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    client.patch(
        "/v1/participants/me/preferences",
        headers=participant_headers(participant),
        json={"study_frequency": "weekly"},
    )
    me = client.get("/v1/participants/me", headers=participant_headers(participant))
    assert me.status_code == 200
    assert me.json()["study_frequency"] == "weekly"


def test_researcher_dashboard_includes_schedule_labels(
    client: TestClient,
    db: Session,
    researcher,
) -> None:
    participant = enrolled(client, db)
    client.patch(
        "/v1/participants/me/preferences",
        headers=participant_headers(participant),
        json={"study_frequency": "twice_weekly"},
    )
    response = client.get(
        "/v1/research/dashboard/participants",
        headers=researcher_headers(researcher),
        params={"limit": 20, "offset": 0},
    )
    assert response.status_code == 200
    row = next(item for item in response.json()["items"] if item["participantId"] == participant.public_id)
    assert row["studyFrequency"] == "twice_weekly"
    assert row["studyFrequencyLabel"] == "Twice a Week"


def test_removed_participant_cannot_update_preferences(
    client: TestClient,
    db: Session,
    researcher,
) -> None:
    from app.services.participant_account_service import remove_participant_access

    participant = enrolled(client, db)
    headers = participant_headers(participant)
    remove_participant_access(
        db,
        public_id=participant.public_id,
        researcher=researcher,
        reason="testing removal",
        confirmation_public_id=participant.public_id,
    )
    response = client.patch(
        "/v1/participants/me/preferences",
        headers=headers,
        json={"study_frequency": "daily"},
    )
    assert response.status_code == 401
