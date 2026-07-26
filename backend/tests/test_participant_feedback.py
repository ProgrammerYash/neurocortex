from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.researcher import Researcher
from app.services.groq_feedback_service import FEEDBACK_WARNING, GroqFeedbackModel
from app.utils.security import create_researcher_access_token
from tests.test_electronic_consent import register



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


def test_participant_feedback_not_released_by_default(client: TestClient):
    registered = register(client)
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    response = client.get("/v1/participants/me/model-feedback", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "not_released"


def test_release_makes_feedback_visible(client: TestClient, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
    participant_headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    mock_model = GroqFeedbackModel(
        status="available",
        level="moderate",
        headline="Moderate strain indicators",
        summary="Your recent study activity shows some patterns associated with cognitive strain.",
        factors=["Reaction-time variation"],
    )
    with patch("app.services.participant_feedback_service.generate_groq_feedback", return_value=(mock_model, "req-1")), patch(
        "app.services.participant_feedback_service.build_deidentified_metric_summary",
        return_value={"completed_session_count": 2, "metrics": {}},
    ), patch(
        "app.services.participant_feedback_service.load_completed_sessions",
        return_value=[],
    ), patch(
        "app.services.participant_feedback_service.get_groq_provider_status",
        return_value={"configured": True, "status": "ready", "model": "test-model", "provider": "Groq"},
    ):
        release = client.post(
            f"/v1/research/participants/{public_id}/feedback/release",
            headers=researcher_headers(researcher),
        )
    assert release.status_code == 200

    response = client.get("/v1/participants/me/model-feedback", headers=participant_headers)
    body = response.json()
    assert body["status"] == "available"
    assert body["level"] == "moderate"
    assert body["warning"] == FEEDBACK_WARNING
    assert "api" not in body.get("summary", "").lower()


def test_revoke_hides_feedback(client: TestClient, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
    participant_headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    mock_model = GroqFeedbackModel(
        status="insufficient_data",
        level=None,
        headline="Not enough data yet",
        summary="Complete at least one full study session before feedback can be generated.",
        factors=[],
    )
    with patch("app.services.participant_feedback_service.generate_groq_feedback", return_value=(mock_model, None)), patch(
        "app.services.participant_feedback_service.build_deidentified_metric_summary",
        return_value={"completed_session_count": 0},
    ), patch(
        "app.services.participant_feedback_service.load_completed_sessions",
        return_value=[],
    ), patch(
        "app.services.participant_feedback_service.get_groq_provider_status",
        return_value={"configured": True, "status": "ready", "model": "test-model", "provider": "Groq"},
    ):
        client.post(
            f"/v1/research/participants/{public_id}/feedback/release",
            headers=researcher_headers(researcher),
        )
        client.post(
            f"/v1/research/participants/{public_id}/feedback/revoke",
            headers=researcher_headers(researcher),
        )

    response = client.get("/v1/participants/me/model-feedback", headers=participant_headers)
    assert response.json()["status"] == "not_released"


def test_groq_provider_status_never_returns_api_key(client: TestClient, researcher: Researcher):
    with patch(
        "app.services.groq_provider_service.get_groq_provider_status",
        return_value={
            "configured": True,
            "status": "ready",
            "model": "llama-test",
            "provider": "Groq",
            "error": None,
        },
    ):
        response = client.get("/v1/research/feedback/provider-status", headers=researcher_headers(researcher))
    assert response.status_code == 200
    body = response.json()
    assert "api_key" not in body
    assert body["provider"] == "Groq"
