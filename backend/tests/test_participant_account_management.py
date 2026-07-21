from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.consent_record import ConsentRecord
from app.models.participant import Participant
from app.models.participant_account_action import ParticipantAccountAction
from app.models.researcher import Researcher
from app.services.participant_account_service import clear_expired_suspension
from app.utils.security import create_access_token, hash_pin, verify_pin
from tests.test_electronic_consent import register, registration_payload
from tests.test_researcher_dashboard import add_session, researcher_headers


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
    researcher = Researcher(display_name="Account Tester", email=f"{uuid4()}@example.test")
    db.add(researcher)
    db.commit()
    return researcher


def enrolled(client: TestClient, db: Session) -> Participant:
    response = register(client, registration_payload(idempotency_key=str(uuid4())))
    assert response.status_code == 201, response.text
    return db.execute(
        select(Participant).where(Participant.public_id == response.json()["public_id"])
    ).scalar_one()


def participant_token(participant: Participant) -> str:
    return create_access_token(
        participant_id=participant.id,
        public_id=participant.public_id,
        auth_version=participant.auth_version,
    )


def test_suspend_requires_reason(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    response = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=headers,
        json={"duration": "24_hours", "reason": "ab"},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("duration", "action_type"),
    [
        ("24_hours", "suspend_24_hours"),
        ("48_hours", "suspend_48_hours"),
        ("1_week", "suspend_1_week"),
        ("1_month", "suspend_1_month"),
        ("indefinite", "suspend_indefinitely"),
    ],
)
def test_researcher_can_suspend_for_durations(
    client: TestClient,
    db: Session,
    researcher: Researcher,
    duration: str,
    action_type: str,
):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    response = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=headers,
        json={"duration": duration, "reason": "Policy violation during testing"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["isSuspended"] is True
    assert body["suspensionReason"] == "Policy violation during testing"
    if duration == "indefinite":
        assert body["suspendedUntil"] is None
    else:
        assert body["suspendedUntil"] is not None

    db.refresh(participant)
    assert participant.is_suspended is True
    assert participant.auth_version >= 2

    actions = db.execute(
        select(ParticipantAccountAction).where(
            ParticipantAccountAction.participant_id == participant.id,
            ParticipantAccountAction.action_type == action_type,
        )
    ).scalars().all()
    assert len(actions) == 1
    assert "pin" not in actions[0].resulting_state


def test_participant_login_and_token_blocked_while_suspended(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant = enrolled(client, db)
    old_token = participant_token(participant)
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=researcher_headers(researcher),
        json={"duration": "24_hours", "reason": "Temporary hold"},
    )
    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 401
    assert login.json()["detail"]["error_code"] == "ACCOUNT_SUSPENDED"

    protected = client.get(
        "/v1/participants/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert protected.status_code == 401
    assert protected.json()["detail"]["error_code"] == "TOKEN_REVOKED"


def test_timed_suspension_expires_automatically(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=researcher_headers(researcher),
        json={"duration": "24_hours", "reason": "Short hold"},
    )
    db.refresh(participant)
    participant.suspended_until = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    clear_expired_suspension(participant, db=db)
    db.commit()
    db.refresh(participant)
    assert participant.is_suspended is False

    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 200


def test_unsuspend_restores_access(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=researcher_headers(researcher),
        json={"duration": "indefinite", "reason": "Manual review"},
    )
    response = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/unsuspend",
        headers=headers,
        json={"reason": "Review complete"},
    )
    assert response.status_code == 200
    assert response.json()["isSuspended"] is False
    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 200


def test_disable_and_enable_account(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    token = participant_token(participant)
    disable = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/disable",
        headers=headers,
        json={"reason": "Administrative disable"},
    )
    assert disable.status_code == 200
    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 401
    assert login.json()["detail"]["error_code"] == "ACCOUNT_DISABLED"
    blocked = client.get("/v1/participants/me", headers={"Authorization": f"Bearer {token}"})
    assert blocked.json()["detail"]["error_code"] == "TOKEN_REVOKED"

    enable = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/enable",
        headers=headers,
        json={"reason": "Issue resolved"},
    )
    assert enable.status_code == 200
    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 200


def test_enable_does_not_bypass_active_suspension(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=headers,
        json={"duration": "24_hours", "reason": "Still suspended"},
    )
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/disable",
        headers=headers,
        json={"reason": "Also disabled"},
    )
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/enable",
        headers=headers,
        json={"reason": "Re-enabled but still suspended"},
    )
    detail = client.get(
        f"/v1/research/dashboard/participants/{participant.public_id}",
        headers=headers,
    )
    assert detail.json()["status"] == "Suspended"
    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.json()["detail"]["error_code"] == "ACCOUNT_SUSPENDED"


def test_reset_pin_flow(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    old_token = participant_token(participant)
    reset = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/reset-pin",
        headers=headers,
    )
    assert reset.status_code == 200
    temp_pin = reset.json()["temporaryPin"]
    assert temp_pin and temp_pin.isdigit()
    assert len(temp_pin) == 6

    db.refresh(participant)
    assert participant.must_change_pin is True
    assert verify_pin(temp_pin, participant.pin_hash)
    assert not verify_pin("2468", participant.pin_hash)

    stale = client.get("/v1/participants/me/sessions", headers={"Authorization": f"Bearer {old_token}"})
    assert stale.json()["detail"]["error_code"] == "TOKEN_REVOKED"

    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": temp_pin},
    )
    assert login.status_code == 200
    assert login.json()["must_change_pin"] is True
    token = login.json()["access_token"]

    blocked = client.get("/v1/participants/me/sessions", headers={"Authorization": f"Bearer {token}"})
    assert blocked.json()["detail"]["error_code"] == "PIN_CHANGE_REQUIRED"

    changed = client.post(
        "/v1/auth/participant/change-pin",
        headers={"Authorization": f"Bearer {token}"},
        json={"pin": "1357", "pin_confirmation": "1357"},
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_pin"] is False

    login_new = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "1357"},
    )
    assert login_new.status_code == 200


def test_remove_account_requires_confirmation(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    add_session(db, participant, datetime.now(UTC).date(), {"reaction": {"avg": 250, "trials": 20}})
    db.commit()
    consent_count = db.execute(
        select(ConsentRecord).where(ConsentRecord.participant_id == participant.id)
    ).scalars().all()

    bad = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/remove-account",
        headers=headers,
        json={"reason": "Requested removal", "confirmation_public_id": "WRONG-ID"},
    )
    assert bad.status_code == 400

    removed = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/remove-account",
        headers=headers,
        json={"reason": "Requested removal", "confirmation_public_id": participant.public_id},
    )
    assert removed.status_code == 200
    assert removed.json()["isRemoved"] is True

    login = client.post(
        "/v1/auth/participant/login",
        json={"public_id": participant.public_id, "pin": "2468"},
    )
    assert login.status_code == 401

    default_list = client.get("/v1/research/dashboard/participants", headers=headers)
    assert all(item["participantId"] != participant.public_id for item in default_list.json()["items"])

    removed_list = client.get(
        "/v1/research/dashboard/participants?status=removed",
        headers=headers,
    )
    assert any(item["participantId"] == participant.public_id for item in removed_list.json()["items"])

    assert len(consent_count) >= 1
    assert db.execute(
        select(ConsentRecord).where(ConsentRecord.participant_id == participant.id)
    ).scalars().all()


def test_participant_token_receives_403_on_researcher_account_endpoints(
    client: TestClient,
    db: Session,
):
    participant = enrolled(client, db)
    headers = {"Authorization": f"Bearer {participant_token(participant)}"}
    response = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=headers,
        json={"duration": "24_hours", "reason": "Should fail"},
    )
    assert response.status_code == 403


def test_audit_records_created_without_sensitive_data(client: TestClient, db: Session, researcher: Researcher):
    participant = enrolled(client, db)
    headers = researcher_headers(researcher)
    client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/disable",
        headers=headers,
        json={"reason": "Audit trail check"},
    )
    actions = client.get(
        f"/v1/research/dashboard/participants/{participant.public_id}/account-actions",
        headers=headers,
    )
    assert actions.status_code == 200
    assert len(actions.json()["items"]) >= 1
    text = actions.text.lower()
    assert "temporarypin" not in text
    assert "pin_hash" not in text
    assert "access_token" not in text
