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
    researcher = Researcher(display_name="Feedback Tester", email=f"{uuid4()}@example.test")
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


def test_feedback_disabled_by_default(client: TestClient):
    registered = register(client)
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    response = client.get("/v1/participants/me/model-feedback", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"


def test_feedback_available_when_enabled_and_model_configured(client: TestClient, researcher: Researcher):
    registered = register(client)
    participant_headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    client.patch(
        "/v1/research/study-settings",
        headers=researcher_headers(researcher),
        json={"participant_feedback_enabled": True},
    )

    with patch("app.services.participant_feedback_service.model_is_configured", return_value=True), patch(
        "app.services.participant_feedback_service.run_fixed_model_inference",
        return_value=(0.42, "moderate", "Moderate estimated cognitive strain", "test-v1"),
    ), patch(
        "app.services.participant_feedback_service.extract_session_features",
        return_value=({"feature_a": 1.0}, []),
    ), patch(
        "app.services.participant_feedback_service._latest_completed_session",
        return_value=object(),
    ):
        response = client.get("/v1/participants/me/model-feedback", headers=participant_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "available"
    assert body["category"] == "moderate"
    assert body["model_version"] == "test-v1"
    assert "path" not in body


def test_fixed_model_utils_do_not_expose_training_methods():
    from app.services import ml_engine_utils

    assert not hasattr(ml_engine_utils, "fit")
    assert not hasattr(ml_engine_utils, "partial_fit")
