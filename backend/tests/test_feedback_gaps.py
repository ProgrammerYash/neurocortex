from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.participant import Participant
from app.models.researcher import Researcher
from app.services.feedback_generation_lock import release_feedback_generation_lock, try_acquire_feedback_generation_lock
from app.services.groq_feedback_service import GroqFeedbackError, GroqFeedbackModel, generate_groq_feedback
from app.services.participant_feedback_service import resolve_researcher_feedback_status
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
    researcher = Researcher(display_name="Gap Tester", email=f"{uuid4()}@example.test")
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


def test_groq_auth_failure_does_not_retry():
    calls = {"n": 0}

    def fail_create(**kwargs):
        calls["n"] += 1
        raise Exception("401 Unauthorized invalid api key")

    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 5
        groq_cls.return_value.chat.completions.create.side_effect = fail_create
        with pytest.raises(GroqFeedbackError) as exc:
            generate_groq_feedback({"completed_session_count": 2})
    assert exc.value.code == "AUTH_FAILURE"
    assert calls["n"] == 1


def test_groq_rate_limit_raises_without_endless_retry():
    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 5
        groq_cls.return_value.chat.completions.create.side_effect = Exception("429 rate limit exceeded")
        with pytest.raises(GroqFeedbackError) as exc:
            generate_groq_feedback({"completed_session_count": 1})
    assert exc.value.code == "RATE_LIMIT"


def test_groq_retry_limit_respected():
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        raise TimeoutError("temporary timeout")

    with patch("app.services.groq_feedback_service.get_settings") as settings, patch("groq.Groq") as groq_cls:
        settings.return_value.groq_api_key = "test-key"
        settings.return_value.groq_model = "test-model"
        settings.return_value.groq_timeout_seconds = 30
        settings.return_value.groq_max_retries = 2
        groq_cls.return_value.chat.completions.create.side_effect = flaky
        with pytest.raises(GroqFeedbackError):
            generate_groq_feedback({"completed_session_count": 1})
    assert calls["n"] == 3


def test_concurrent_duplicate_generation(client: TestClient, db: Session, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
    participant = db.execute(select(Participant).where(Participant.public_id == public_id)).scalar_one()

    assert try_acquire_feedback_generation_lock(db, participant.id) is True
    try:
        mock_model = GroqFeedbackModel(
            status="available",
            level="low",
            headline="Lower strain indicators",
            summary="Summary.",
            factors=[],
        )
        with patch("app.services.participant_feedback_service.generate_groq_feedback", return_value=(mock_model, "r1")), patch(
            "app.services.participant_feedback_service.build_deidentified_metric_summary",
            return_value={"completed_session_count": 1},
        ), patch(
            "app.services.participant_feedback_service.load_completed_sessions",
            return_value=[],
        ), patch(
            "app.services.participant_feedback_service.get_groq_provider_status",
            return_value={"configured": True, "status": "ready", "model": "m"},
        ):
            response = client.post(
                f"/v1/research/participants/{public_id}/feedback/release",
                headers=researcher_headers(researcher),
            )
        assert response.status_code == 409
    finally:
        release_feedback_generation_lock(db, participant.id)


def test_dashboard_lists_feedback_status(client: TestClient, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
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
        return_value={"configured": True, "status": "ready", "model": "m"},
    ):
        client.post(
            f"/v1/research/participants/{public_id}/feedback/release",
            headers=researcher_headers(researcher),
        )
    listing = client.get("/v1/research/dashboard/participants?limit=20&offset=0", headers=researcher_headers(researcher))
    item = next(row for row in listing.json()["items"] if row["participantId"] == public_id)
    assert item["feedbackStatus"] == "Insufficient Data"


def test_refresh_failure_preserves_released_snapshot(client: TestClient, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
    good = GroqFeedbackModel(
        status="available",
        level="moderate",
        headline="Moderate strain indicators",
        summary="First release.",
        factors=[],
    )
    with patch("app.services.participant_feedback_service.generate_groq_feedback", return_value=(good, "r1")), patch(
        "app.services.participant_feedback_service.build_deidentified_metric_summary",
        return_value={"completed_session_count": 2},
    ), patch(
        "app.services.participant_feedback_service.load_completed_sessions",
        return_value=[],
    ), patch(
        "app.services.participant_feedback_service.get_groq_provider_status",
        return_value={"configured": True, "status": "ready", "model": "m"},
    ):
        client.post(
            f"/v1/research/participants/{public_id}/feedback/release",
            headers=researcher_headers(researcher),
        )

    with patch(
        "app.services.participant_feedback_service.generate_groq_feedback",
        side_effect=GroqFeedbackError("fail", code="PROVIDER_FAILURE"),
    ), patch(
        "app.services.participant_feedback_service.build_deidentified_metric_summary",
        return_value={"completed_session_count": 2},
    ), patch(
        "app.services.participant_feedback_service.load_completed_sessions",
        return_value=[],
    ), patch(
        "app.services.participant_feedback_service.get_groq_provider_status",
        return_value={"configured": True, "status": "ready", "model": "m"},
    ):
        refresh = client.post(
            f"/v1/research/participants/{public_id}/feedback/refresh",
            headers=researcher_headers(researcher),
        )
    assert refresh.status_code == 502
    participant_headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    view = client.get("/v1/participants/me/model-feedback", headers=participant_headers)
    assert view.json()["status"] == "available"
    assert view.json()["headline"] == "Moderate strain indicators"


def test_bulk_partial_release_failure(client: TestClient, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
    mock_model = GroqFeedbackModel(
        status="available",
        level="low",
        headline="Lower strain indicators",
        summary="Ok",
        factors=[],
    )

    def metrics_for(db, participant):
        return {"completed_session_count": 2}

    with patch("app.services.participant_feedback_service.generate_groq_feedback", return_value=(mock_model, "x")), patch(
        "app.services.participant_feedback_service.build_deidentified_metric_summary",
        side_effect=metrics_for,
    ), patch(
        "app.services.participant_feedback_service.load_completed_sessions",
        return_value=[],
    ), patch(
        "app.services.participant_feedback_service.get_groq_provider_status",
        return_value={"configured": True, "status": "ready", "model": "m"},
    ):
        response = client.post(
            "/v1/research/participants/feedback/release-bulk",
            headers=researcher_headers(researcher),
            json={"participant_public_ids": [public_id, "NC-NOTREAL999"]},
        )
    body = response.json()
    assert body["skipped_count"] >= 1
    assert body["succeeded_count"] >= 1


def test_total_completed_sessions_separate_from_weekly_progress(client: TestClient, researcher: Researcher, db: Session):
    from datetime import date

    from app.services.procedure_service import build_participant_study_progress, count_all_study_completed_sessions
    from app.services.study_week import weekly_session_target

    registered = register(client)
    public_id = registered.json()["public_id"]
    participant = db.execute(select(Participant).where(Participant.public_id == public_id)).scalar_one()
    total_all = count_all_study_completed_sessions(db)
    weekly = build_participant_study_progress(
        db,
        participant_id=participant.id,
        session_date=date.today(),
        consent_eligible=True,
        consent_block_reason=None,
        consent_block_message=None,
        withdrawal_status="none",
        study_frequency="daily",
    )
    summary = client.get("/v1/research/dashboard/summary", headers=researcher_headers(researcher))
    assert summary.json()["totalCompletedSessions"] == total_all
    assert weekly["weekly_target"] == weekly_session_target("daily")
    assert weekly["completed_this_week"] <= total_all


def test_resolve_revoked_status():
    class Snap:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    latest = Snap(revoked_at="x", is_released=False, error_code=None, status="available")
    assert resolve_researcher_feedback_status(active=None, latest=latest) == "Revoked"
