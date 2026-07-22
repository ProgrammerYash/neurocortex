from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.participant import Participant
from app.services.participant_account_service import remove_participant_access
from app.utils.security import hash_pin
from tests.test_electronic_consent import register, registration_payload


@pytest.fixture()
def researcher(db: Session):
    from app.models.researcher import Researcher

    row = Researcher(display_name="Recent Status Tester", email=f"{uuid4()}@example.test")
    db.add(row)
    db.commit()
    return row


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


def enrolled(client: TestClient, db: Session) -> Participant:
    response = register(client, registration_payload(idempotency_key=str(uuid4())))
    assert response.status_code == 201, response.text
    return db.execute(
        select(Participant).where(Participant.public_id == response.json()["public_id"])
    ).scalar_one()


def test_active_participant_recent_eligible(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    response = client.post(
        "/v1/auth/participant/recent-status",
        json={"public_ids": [participant.public_id, participant.public_id]},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["participants"]) == 1
    assert body["participants"][0]["public_id"] == participant.public_id
    assert body["participants"][0]["recent_eligible"] is True
    assert set(body["participants"][0]) == {"public_id", "recent_eligible"}


def test_removed_participant_not_eligible(client: TestClient, db: Session, researcher) -> None:
    participant = enrolled(client, db)
    remove_participant_access(
        db,
        public_id=participant.public_id,
        researcher=researcher,
        reason="testing removal",
        confirmation_public_id=participant.public_id,
    )
    response = client.post(
        "/v1/auth/participant/recent-status",
        json={"public_ids": [participant.public_id]},
    )
    assert response.status_code == 200
    assert response.json()["participants"][0]["recent_eligible"] is False


def test_unknown_public_id_not_eligible(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/participant/recent-status",
        json={"public_ids": ["NC-NOTREAL12345"]},
    )
    assert response.status_code == 200
    assert response.json()["participants"][0]["recent_eligible"] is False


def test_empty_list_returns_empty(client: TestClient) -> None:
    response = client.post("/v1/auth/participant/recent-status", json={"public_ids": []})
    assert response.status_code == 200
    assert response.json()["participants"] == []


def test_oversized_list_truncated(client: TestClient) -> None:
    ids = [f"NC-{i:06d}" for i in range(25)]
    response = client.post("/v1/auth/participant/recent-status", json={"public_ids": ids})
    assert response.status_code == 200
    assert len(response.json()["participants"]) <= 20


def test_invalid_ids_filtered(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    response = client.post(
        "/v1/auth/participant/recent-status",
        json={"public_ids": ["bad-id", participant.public_id, ""]},
    )
    assert response.status_code == 200
    assert len(response.json()["participants"]) == 1


def test_does_not_require_auth(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    response = client.post(
        "/v1/auth/participant/recent-status",
        json={"public_ids": [participant.public_id]},
    )
    assert response.status_code == 200


def test_login_endpoint_unaffected(client: TestClient, db: Session) -> None:
    participant = enrolled(client, db)
    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 200
    assert login.json()["public_id"] == participant.public_id
