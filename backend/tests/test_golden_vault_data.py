from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant_feedback_snapshot import ParticipantFeedbackSnapshot
from app.services.golden_vault_service import enable_override, regenerate_metrics
from app.utils.security import create_golden_vault_access_token, hash_invite_code
from tests.test_electronic_consent import register
from tests.test_researcher_dashboard import (
    participant_by_public_id,
    researcher,
    researcher_headers,
)


@pytest.fixture()
def vault_env(monkeypatch):
    code = f"vault-{uuid4()}"
    monkeypatch.setenv("GOLDEN_VAULT_ENABLED", "true")
    monkeypatch.setenv("GOLDEN_VAULT_CODE_HASH", hash_invite_code(code))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def vault_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_golden_vault_access_token()}"}


def test_enabling_creates_single_override_row(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    enable_override(db, public_id=public_id)
    participant = participant_by_public_id(db, public_id)
    rows = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].enabled is True


def test_metrics_persist_and_regenerate(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    first_reaction = row.simulated_reaction_ms
    assert 230 <= first_reaction <= 650
    regenerate_metrics(db, public_id=public_id)
    db.refresh(row)
    second_reaction = row.simulated_reaction_ms
    assert second_reaction is not None
    assert 230 <= second_reaction <= 650


def test_display_sessions_and_coins(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    login = participant_by_public_id(db, public_id)
    client.put(
        f"/v1/participants/me/game",
        headers={"Authorization": f"Bearer {__import__('app.utils.security', fromlist=['create_access_token']).create_access_token(participant_id=login.id, public_id=public_id)}"},
        json={
            "coins": 120,
            "streak": 1,
            "longestStreak": 1,
            "totalDays": 2,
            "lastCompleted": "2026-01-01",
            "pet": {"type": "fox", "xp": 0, "level": 1},
            "house": {"items": []},
            "achievements": [],
            "unlockedRegions": [],
        },
    )
    enable_override(db, public_id=public_id)
    row = db.execute(select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == login.id)).scalar_one()
    row.bonus_sessions = 50
    row.bonus_coins = 500
    db.commit()

    dash = client.get("/v1/research/dashboard/participants", headers=researcher_headers(researcher))
    assert dash.status_code == 200
    item = next(i for i in dash.json()["items"] if i["participantId"] == public_id)
    assert item["isDemoOverride"] is True
    assert item["sessions"] == 50
    assert item["realCompletedSessions"] == 0
    assert item["bonusSessions"] == 50
    assert item["feedbackStatus"] in {"Released", "Not Released", "Revoked"}


def test_bonus_cannot_go_negative(client: TestClient, db: Session, vault_env):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    headers = vault_headers()
    response = client.post(
        f"/v1/golden-vault/participants/{public_id}/sessions",
        headers=headers,
        json={"delta": -999},
    )
    assert response.status_code == 200
    assert response.json()["bonusSessions"] == 0


def test_simulated_feedback_no_groq(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    row.is_auto_data_user = True
    row.simulated_feedback_status = "Released"
    db.flush()
    token = __import__("app.utils.security", fromlist=["create_access_token"]).create_access_token(
        participant_id=participant.id,
        public_id=public_id,
    )
    with patch("app.services.groq_feedback_service.generate_groq_feedback") as groq_mock:
        feedback = client.get("/v1/participants/me/model-feedback", headers={"Authorization": f"Bearer {token}"})
        assert feedback.status_code == 200
        body = feedback.json()
        assert body.get("isSimulated") is True
        assert body["status"] == "available"
        groq_mock.assert_not_called()
    snapshots = db.execute(
        select(ParticipantFeedbackSnapshot).where(ParticipantFeedbackSnapshot.participant_id == participant.id)
    ).scalars().all()
    assert snapshots == []


def test_researcher_dashboard_detail_uses_golden_overlay(client: TestClient, db: Session, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    row.bonus_sessions = 50
    db.flush()
    detail = client.get(
        f"/v1/research/dashboard/participants/{public_id}",
        headers=researcher_headers(researcher),
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["isDemoOverride"] is True
    assert body["sessionsCompleted"] >= 50
    assert body["feedbackStatus"] != "Insufficient Data"


def test_bulk_partial_report(client: TestClient, db: Session, vault_env):
    public_id = register(client).json()["public_id"]
    headers = vault_headers()
    result = client.post(
        "/v1/golden-vault/participants/bulk",
        headers=headers,
        json={
            "action": "add_sessions",
            "participant_public_ids": [public_id, "NOTREAL1"],
            "amount": 5,
        },
    ).json()
    assert result["requested_count"] == 2
    assert result["succeeded_count"] == 1
    assert result["skipped_count"] == 1
