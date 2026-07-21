from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.participant import Participant
from app.models.participant_message import ParticipantMessage
from app.models.researcher import Researcher
from app.utils.security import create_access_token
from tests.test_electronic_consent import register, registration_payload
from tests.test_researcher_dashboard import researcher_headers


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
    researcher = Researcher(display_name="Message Tester", email=f"{uuid4()}@example.test")
    db.add(researcher)
    db.commit()
    return researcher


def enrolled(client: TestClient, db: Session) -> tuple[Participant, str]:
    response = register(client, registration_payload(idempotency_key=str(uuid4())))
    assert response.status_code == 201, response.text
    participant = db.execute(
        select(Participant).where(Participant.public_id == response.json()["public_id"])
    ).scalar_one()
    return participant, response.json()["access_token"]


def participant_headers(participant: Participant) -> dict[str, str]:
    return {
        "Authorization": "Bearer "
        + create_access_token(
            participant_id=participant.id,
            public_id=participant.public_id,
            auth_version=participant.auth_version,
        )
    }


def send_message(
    client: TestClient,
    *,
    headers: dict[str, str],
    public_id: str,
    subject: str = "Study update",
    body: str = "Please complete today's assessment.",
):
    return client.post(
        f"/v1/research/dashboard/participants/{public_id}/messages",
        headers=headers,
        json={"subject": subject, "body": body},
    )


def test_researcher_can_send_valid_message(client: TestClient, db: Session, researcher: Researcher):
    participant, _ = enrolled(client, db)
    response = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["subject"] == "Study update"
    assert body["participantId"] == participant.public_id
    assert body["isRead"] is False
    assert "id" in body
    assert str(participant.id) not in response.text


def test_participant_token_receives_403_from_researcher_send_endpoint(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant, token = enrolled(client, db)
    response = send_message(
        client,
        headers={"Authorization": f"Bearer {token}"},
        public_id=participant.public_id,
    )
    assert response.status_code == 403


def test_missing_participant_returns_safe_error(client: TestClient, researcher: Researcher):
    response = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id="NC-MISSING",
    )
    assert response.status_code == 404


def test_removed_participant_cannot_receive_new_message(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant, _ = enrolled(client, db)
    headers = researcher_headers(researcher)
    remove = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/remove-account",
        headers=headers,
        json={"reason": "Requested removal during testing", "confirmation_public_id": participant.public_id},
    )
    assert remove.status_code == 200, remove.text
    response = send_message(client, headers=headers, public_id=participant.public_id)
    assert response.status_code == 409


def test_suspended_participant_may_receive_message_for_later(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant, _ = enrolled(client, db)
    headers = researcher_headers(researcher)
    suspend = client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=headers,
        json={"duration": "24_hours", "reason": "Temporary suspension for testing"},
    )
    assert suspend.status_code == 200, suspend.text
    response = send_message(client, headers=headers, public_id=participant.public_id)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    ("subject", "body"),
    [
        ("   ", "Valid body"),
        ("Valid subject", "   "),
    ],
)
def test_whitespace_only_message_fields_rejected(
    client: TestClient,
    db: Session,
    researcher: Researcher,
    subject: str,
    body: str,
):
    participant, _ = enrolled(client, db)
    response = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
        subject=subject,
        body=body,
    )
    assert response.status_code == 422


def test_subject_length_limit(client: TestClient, db: Session, researcher: Researcher):
    participant, _ = enrolled(client, db)
    response = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
        subject="x" * 151,
        body="Valid body",
    )
    assert response.status_code == 422


def test_body_length_limit(client: TestClient, db: Session, researcher: Researcher):
    participant, _ = enrolled(client, db)
    response = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
        subject="Valid subject",
        body="x" * 5001,
    )
    assert response.status_code == 422


def test_participant_only_sees_own_messages(client: TestClient, db: Session, researcher: Researcher):
    participant_a, token_a = enrolled(client, db)
    participant_b, _ = enrolled(client, db)
    headers = researcher_headers(researcher)
    assert send_message(
        client,
        headers=headers,
        public_id=participant_a.public_id,
        subject="For A",
        body="Message for participant A",
    ).status_code == 201
    assert send_message(
        client,
        headers=headers,
        public_id=participant_b.public_id,
        subject="For B",
        body="Message for participant B",
    ).status_code == 201
    listing = client.get("/v1/participants/me/messages", headers={"Authorization": f"Bearer {token_a}"})
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["subject"] == "For A"


def test_participant_cannot_access_another_participants_message(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant_a, token_a = enrolled(client, db)
    participant_b, _ = enrolled(client, db)
    sent = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant_b.public_id,
        subject="Private",
        body="Only for B",
    )
    message_id = sent.json()["id"]
    response = client.post(
        f"/v1/participants/me/messages/{message_id}/read",
        headers={"Authorization": f"Bearer {token_a}"},
        json={},
    )
    assert response.status_code == 404


def test_unread_count_is_correct(client: TestClient, db: Session, researcher: Researcher):
    participant, token = enrolled(client, db)
    headers = researcher_headers(researcher)
    assert send_message(client, headers=headers, public_id=participant.public_id, subject="One", body="First").status_code == 201
    assert send_message(client, headers=headers, public_id=participant.public_id, subject="Two", body="Second").status_code == 201
    unread = client.get(
        "/v1/participants/me/messages/unread-count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert unread.status_code == 200
    assert unread.json()["unread_count"] == 2


def test_marking_read_updates_read_at(client: TestClient, db: Session, researcher: Researcher):
    participant, token = enrolled(client, db)
    sent = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
    )
    message_id = sent.json()["id"]
    read = client.post(
        f"/v1/participants/me/messages/{message_id}/read",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert read.status_code == 200, read.text
    assert read.json()["isRead"] is True
    assert read.json()["readAt"] is not None


def test_marking_read_twice_is_safe(client: TestClient, db: Session, researcher: Researcher):
    participant, token = enrolled(client, db)
    sent = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
    )
    message_id = sent.json()["id"]
    headers = {"Authorization": f"Bearer {token}"}
    first = client.post(f"/v1/participants/me/messages/{message_id}/read", headers=headers, json={})
    second = client.post(f"/v1/participants/me/messages/{message_id}/read", headers=headers, json={})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["readAt"] == second.json()["readAt"]


def test_researcher_sees_sent_message_history(client: TestClient, db: Session, researcher: Researcher):
    participant, _ = enrolled(client, db)
    headers = researcher_headers(researcher)
    assert send_message(client, headers=headers, public_id=participant.public_id).status_code == 201
    history = client.get(
        f"/v1/research/dashboard/participants/{participant.public_id}/messages",
        headers=headers,
    )
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["subject"] == "Study update"


def test_read_status_reflected_in_researcher_history(client: TestClient, db: Session, researcher: Researcher):
    participant, token = enrolled(client, db)
    headers = researcher_headers(researcher)
    sent = send_message(client, headers=headers, public_id=participant.public_id)
    message_id = sent.json()["id"]
    assert client.post(
        f"/v1/participants/me/messages/{message_id}/read",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    ).status_code == 200
    history = client.get(
        f"/v1/research/dashboard/participants/{participant.public_id}/messages",
        headers=headers,
    )
    assert history.json()["items"][0]["isRead"] is True


def test_messages_contain_no_reply_fields(client: TestClient, db: Session, researcher: Researcher):
    participant, token = enrolled(client, db)
    sent = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
    )
    payload = sent.json()
    forbidden = {"replyTo", "reply_to", "threadId", "thread_id", "parentMessageId", "parent_message_id"}
    assert forbidden.isdisjoint(payload.keys())
    listing = client.get("/v1/participants/me/messages", headers={"Authorization": f"Bearer {token}"})
    assert forbidden.isdisjoint(listing.json()["items"][0].keys())


def test_message_creation_does_not_expose_internal_participant_uuid(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant, _ = enrolled(client, db)
    response = send_message(
        client,
        headers=researcher_headers(researcher),
        public_id=participant.public_id,
    )
    assert response.status_code == 201
    assert response.json()["participantId"] == participant.public_id
    assert str(participant.id) not in response.text


def test_account_removal_preserves_existing_message_records(
    client: TestClient,
    db: Session,
    researcher: Researcher,
):
    participant, _ = enrolled(client, db)
    headers = researcher_headers(researcher)
    assert send_message(client, headers=headers, public_id=participant.public_id).status_code == 201
    assert client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/remove-account",
        headers=headers,
        json={"reason": "Removal preserves history", "confirmation_public_id": participant.public_id},
    ).status_code == 200
    count = db.execute(select(func.count()).select_from(ParticipantMessage)).scalar_one()
    assert count == 1
    history = client.get(
        f"/v1/research/dashboard/participants/{participant.public_id}/messages",
        headers=headers,
    )
    assert history.status_code == 200
    assert history.json()["total"] == 1


def test_suspended_participant_token_blocked_from_inbox(client: TestClient, db: Session, researcher: Researcher):
    participant, _ = enrolled(client, db)
    headers = researcher_headers(researcher)
    assert send_message(client, headers=headers, public_id=participant.public_id).status_code == 201
    assert client.post(
        f"/v1/research/dashboard/participants/{participant.public_id}/suspend",
        headers=headers,
        json={"duration": "24_hours", "reason": "Temporary suspension for testing"},
    ).status_code == 200
    token = participant_headers(participant)
    blocked = client.get("/v1/participants/me/messages", headers=token)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["error_code"] == "ACCOUNT_SUSPENDED"
