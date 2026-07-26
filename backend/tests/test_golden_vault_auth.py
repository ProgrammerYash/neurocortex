from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, get_db
from app.main import app
from app.models.researcher import Researcher
from app.utils.security import (
    create_golden_vault_access_token,
    create_access_token,
    create_researcher_access_token,
    decode_access_token,
    hash_invite_code,
)
from tests.test_electronic_consent import register
from tests.test_researcher_dashboard import researcher, researcher_headers, participant_by_public_id


@pytest.fixture()
def vault_hash(monkeypatch):
    code = f"vault-{uuid4()}"
    monkeypatch.setenv("GOLDEN_VAULT_ENABLED", "true")
    monkeypatch.setenv("GOLDEN_VAULT_CODE_HASH", hash_invite_code(code))
    monkeypatch.setenv("GOLDEN_VAULT_TOKEN_MINUTES", "30")
    get_settings.cache_clear()
    yield code
    get_settings.cache_clear()


def golden_headers(minutes: int = 30) -> dict[str, str]:
    token = create_golden_vault_access_token(expires_minutes=minutes)
    return {"Authorization": f"Bearer {token}"}


def test_vault_disabled_rejects_login(client: TestClient, monkeypatch):
    monkeypatch.setenv("GOLDEN_VAULT_ENABLED", "false")
    get_settings.cache_clear()
    response = client.post("/v1/golden-vault/login", json={"code": "anything"})
    assert response.status_code == 401
    get_settings.cache_clear()


def test_correct_hash_accepts_login(client: TestClient, db: Session, vault_hash: str):
    response = client.post("/v1/golden-vault/login", json={"code": vault_hash})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert "access_token" in body


def test_incorrect_code_rejected(client: TestClient, vault_hash: str):
    response = client.post("/v1/golden-vault/login", json={"code": "wrong-code"})
    assert response.status_code == 401


def test_golden_token_scope(client: TestClient, vault_hash: str):
    login = client.post("/v1/golden-vault/login", json={"code": vault_hash}).json()
    token = login["access_token"]
    payload = decode_access_token(token)
    assert payload["role"] == "golden_vault"
    assert payload["scope"] == "golden_vault"


def test_researcher_token_rejected_on_golden_routes(client: TestClient, researcher: Researcher):
    response = client.get(
        "/v1/golden-vault/participants",
        headers=researcher_headers(researcher),
    )
    assert response.status_code == 403


def test_participant_token_rejected(client: TestClient, db: Session):
    registered = register(client)
    public_id = registered.json()["public_id"]
    participant = participant_by_public_id(db, public_id)
    token = create_access_token(participant_id=participant.id, public_id=public_id)
    response = client.get(
        "/v1/golden-vault/participants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_golden_token_cannot_access_researcher_dashboard(client: TestClient, vault_hash: str):
    login = client.post("/v1/golden-vault/login", json={"code": vault_hash}).json()
    response = client.get(
        "/v1/research/dashboard/summary",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert response.status_code == 403


def test_expired_golden_token_rejected(client: TestClient):
    token = create_golden_vault_access_token(expires_minutes=-1)
    response = client.get(
        "/v1/golden-vault/participants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_rate_limiting_blocks_repeated_failures(client: TestClient, vault_hash: str, monkeypatch):
    from app.services import golden_vault_rate_limit as rl

    rl.reset_golden_vault_login_attempts("testclient")
    monkeypatch.setattr(rl, "_MAX_ATTEMPTS", 3)
    for _ in range(3):
        client.post("/v1/golden-vault/login", json={"code": "bad"})
    blocked = client.post("/v1/golden-vault/login", json={"code": vault_hash})
    assert blocked.status_code == 429
    rl.reset_golden_vault_login_attempts("testclient")
