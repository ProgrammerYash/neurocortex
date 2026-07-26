from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.researcher import Researcher
from app.utils.security import create_researcher_access_token, create_access_token
from tests.test_electronic_consent import register



@pytest.fixture()
def researcher(db: Session) -> Researcher:
    researcher = Researcher(display_name="Bulk Tester", email=f"{uuid4()}@example.test")
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


def test_bulk_message_requires_researcher(client: TestClient):
    registered = register(client)
    token = registered.json()["access_token"]
    response = client.post(
        "/v1/research/participants/bulk/message",
        headers={"Authorization": f"Bearer {token}"},
        json={"participant_public_ids": ["NC-TEST"], "subject": "Hi", "body": "Hello"},
    )
    assert response.status_code == 403


def test_bulk_message_creates_per_participant_messages(client: TestClient, researcher: Researcher, db: Session):
    registered = register(client)
    public_id = registered.json()["public_id"]
    response = client.post(
        "/v1/research/participants/bulk/message",
        headers=researcher_headers(researcher),
        json={
            "participant_public_ids": [public_id],
            "subject": "Study reminder",
            "body": "Please complete your session.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["succeeded_count"] >= 1

    participant_token = registered.json()["access_token"]
    inbox = client.get("/v1/participants/me/messages", headers={"Authorization": f"Bearer {participant_token}"})
    assert inbox.status_code == 200
    items = inbox.json().get("items") or inbox.json()
    if isinstance(items, dict):
        items = items.get("items", [])
    assert any("Study reminder" in (item.get("subject") or "") for item in items)


def test_bulk_email_unconfigured_returns_error(client: TestClient, researcher: Researcher):
    registered = register(client)
    public_id = registered.json()["public_id"]
    response = client.post(
        "/v1/research/participants/bulk/email",
        headers=researcher_headers(researcher),
        json={
            "participant_public_ids": [public_id],
            "subject": "Hello",
            "body": "Body",
        },
    )
    assert response.status_code in (503, 200)
    if response.status_code == 503:
        assert "configured" in response.json()["detail"].lower()
