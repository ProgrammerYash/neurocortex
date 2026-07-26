from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.researcher import Researcher
from app.utils.security import create_researcher_access_token
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
    researcher = Researcher(display_name="Groq Settings Tester", email=f"{uuid4()}@example.test")
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


def test_groq_provider_status_requires_researcher(client: TestClient):
    assert client.get("/v1/research/feedback/provider-status").status_code == 401


def test_groq_provider_status_not_configured(client: TestClient, researcher: Researcher):
    with patch(
        "app.routers.research.get_groq_provider_status",
        return_value={"configured": False, "status": "not_configured", "model": None, "provider": "Groq"},
    ):
        response = client.get("/v1/research/feedback/provider-status", headers=researcher_headers(researcher))
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_participant_cannot_read_groq_provider_status(client: TestClient):
    registered = register(client)
    token = registered.json()["access_token"]
    response = client.get(
        "/v1/research/feedback/provider-status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_legacy_study_settings_routes_removed(client: TestClient, researcher: Researcher):
    headers = researcher_headers(researcher)
    assert client.get("/v1/research/study-settings", headers=headers).status_code == 404
    assert client.patch("/v1/research/study-settings", headers=headers, json={}).status_code == 404
