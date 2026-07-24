from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.researcher import Researcher
from app.utils.security import create_access_token, create_researcher_access_token
from tests.test_electronic_consent import register


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
    researcher = Researcher(display_name="Settings Tester", email=f"{uuid4()}@example.test")
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


def test_feedback_setting_defaults_off(client: TestClient, researcher: Researcher):
    response = client.get("/v1/research/study-settings", headers=researcher_headers(researcher))
    assert response.status_code == 200
    body = response.json()
    assert body["participant_feedback_enabled"] is False
    assert body["model_configured"] is False


def test_researcher_can_enable_and_disable_feedback(client: TestClient, researcher: Researcher):
    headers = researcher_headers(researcher)
    enabled = client.patch(
        "/v1/research/study-settings",
        headers=headers,
        json={"participant_feedback_enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["participant_feedback_enabled"] is True
    assert enabled.json()["participant_feedback_updated_by"] == str(researcher.id)

    disabled = client.patch(
        "/v1/research/study-settings",
        headers=headers,
        json={"participant_feedback_enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["participant_feedback_enabled"] is False


def test_participant_cannot_update_study_settings(client: TestClient):
    registered = register(client)
    token = registered.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        "/v1/research/study-settings",
        headers=headers,
        json={"participant_feedback_enabled": True},
    )
    assert response.status_code == 403


def test_unauthenticated_study_settings_rejected(client: TestClient):
    assert client.get("/v1/research/study-settings").status_code == 401
    assert client.patch("/v1/research/study-settings", json={"participant_feedback_enabled": True}).status_code == 401


def test_invalid_study_settings_payload_rejected(client: TestClient, researcher: Researcher):
    response = client.patch(
        "/v1/research/study-settings",
        headers=researcher_headers(researcher),
        json={"participant_feedback_enabled": "yes"},
    )
    assert response.status_code == 422
