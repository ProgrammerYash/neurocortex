from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.participant_age import MAX_PARTICIPANT_AGE, MIN_PARTICIPANT_AGE
from app.database import engine, get_db
from app.main import app
from app.models.participant import Participant
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


@pytest.mark.parametrize(
    "age,category",
    [(11, "under_18"), (12, "under_18"), (MAX_PARTICIPANT_AGE, "age_18_or_over")],
)
def test_registration_accepts_valid_ages(client: TestClient, db: Session, age: int, category: str):
    response = register(client, registration_payload(age=age, age_consent_category=category))
    assert response.status_code == 201, response.text
    public_id = response.json()["public_id"]
    participant = db.execute(select(Participant).where(Participant.public_id == public_id)).scalar_one()
    assert participant.age_years == age
    assert participant.age_range == str(age)


@pytest.mark.parametrize("payload", [{"age": 10}, {"age": MAX_PARTICIPANT_AGE + 1}, {"age": "13-14"}, {"age": 13.5}])
def test_registration_rejects_invalid_ages(client: TestClient, payload: dict):
    body = registration_payload(**payload)
    response = register(client, body)
    assert response.status_code == 422


def test_registration_requires_age(client: TestClient):
    body = registration_payload()
    body.pop("age")
    response = register(client, body)
    assert response.status_code == 422


def test_age_constants():
    assert MIN_PARTICIPANT_AGE == 11
    assert MAX_PARTICIPANT_AGE == 26
