from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.daily_session import DailySession
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.golden_fake_user_batch import GoldenFakeUserBatch
from app.models.participant import Participant
from app.models.participant_feedback_snapshot import ParticipantFeedbackSnapshot
from app.models.researcher import Researcher
from app.services.golden_vault_fake_user_service import preview_fake_users
from app.utils.security import create_golden_vault_access_token, hash_invite_code, hash_pin
from tests.test_researcher_dashboard import researcher, researcher_headers


@pytest.fixture()
def vault_env(monkeypatch):
    code = f"vault-{uuid4()}"
    monkeypatch.setenv("GOLDEN_VAULT_ENABLED", "true")
    monkeypatch.setenv("GOLDEN_VAULT_CODE_HASH", hash_invite_code(code))
    get_settings.cache_clear()
    yield code
    get_settings.cache_clear()


def vault_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_golden_vault_access_token()}"}


def _run_batch(client: TestClient, body: dict) -> dict:
    created = client.post("/v1/golden-vault/fake-users/generate", json=body, headers=vault_headers())
    assert created.status_code == 200, created.text
    batch_id = created.json()["batchId"]
    status = created.json()["status"]
    while status not in {"completed", "completed_with_errors", "failed"}:
        step = client.post(
            f"/v1/golden-vault/fake-users/batches/{batch_id}/process",
            headers=vault_headers(),
        )
        assert step.status_code == 200, step.text
        status = step.json()["status"]
    return client.get(f"/v1/golden-vault/fake-users/batches/{batch_id}", headers=vault_headers()).json()


def test_fake_users_require_golden_vault_auth(client: TestClient, vault_env, researcher: Researcher):
    body = {
        "total": 1,
        "start_date": "2026-01-01",
        "daily": 1,
        "weekly": 0,
        "two_days": 0,
        "four_days": 0,
    }
    assert client.post("/v1/golden-vault/fake-users/preview", json=body).status_code == 401
    assert (
        client.post(
            "/v1/golden-vault/fake-users/preview",
            json=body,
            headers=researcher_headers(researcher),
        ).status_code
        == 403
    )


def test_fake_user_distribution_validation(client: TestClient, vault_env):
    body = {
        "total": 5,
        "start_date": "2026-01-01",
        "daily": 2,
        "weekly": 2,
        "two_days": 0,
        "four_days": 0,
    }
    response = client.post("/v1/golden-vault/fake-users/preview", json=body, headers=vault_headers())
    assert response.status_code == 400


def test_preview_creates_no_records(client: TestClient, db: Session, vault_env):
    before_participants = db.execute(select(func.count()).select_from(Participant)).scalar_one()
    before_batches = db.execute(select(func.count()).select_from(GoldenFakeUserBatch)).scalar_one()
    body = {
        "total": 3,
        "start_date": "2026-01-10",
        "daily": 1,
        "weekly": 1,
        "two_days": 1,
        "four_days": 0,
    }
    response = client.post("/v1/golden-vault/fake-users/preview", json=body, headers=vault_headers())
    assert response.status_code == 200
    after_participants = db.execute(select(func.count()).select_from(Participant)).scalar_one()
    after_batches = db.execute(select(func.count()).select_from(GoldenFakeUserBatch)).scalar_one()
    assert after_participants == before_participants
    assert after_batches == before_batches


def test_generate_exact_count_ids_pins_and_no_real_sessions(
    client: TestClient,
    db: Session,
    vault_env,
    monkeypatch,
):
    groq_called = {"value": False}

    def _fail_groq(*_args, **_kwargs):
        groq_called["value"] = True
        raise AssertionError("Groq must not be called for fake users")

    monkeypatch.setattr("app.services.groq_feedback_service.generate_groq_feedback", _fail_groq)

    body = {
        "total": 4,
        "start_date": "2026-01-05",
        "daily": 2,
        "weekly": 1,
        "two_days": 1,
        "four_days": 0,
        "idempotency_key": str(uuid4()),
    }
    summary = _run_batch(client, body)
    assert summary["successfulCount"] == 4
    assert summary["processedCount"] == 4

    batch_id = summary["batchId"]
    creds = client.get(
        f"/v1/golden-vault/fake-users/batches/{batch_id}/credentials",
        headers=vault_headers(),
    )
    assert creds.status_code == 200
    items = creds.json()["credentials"]
    assert len(items) == 4
    public_ids = [row["publicId"] for row in items]
    assert len(set(public_ids)) == 4

    participants = db.execute(select(Participant).where(Participant.public_id.in_(public_ids))).scalars().all()
    assert len(participants) == 4
    for participant in participants:
        assert participant.pin_hash
        assert participant.pin_hash != hash_pin("000000")

    participant_ids = [p.id for p in participants]
    for pid in participant_ids:
        assert (
            db.execute(
                select(func.count()).select_from(DailySession).where(DailySession.participant_id == pid)
            ).scalar_one()
            == 0
        )
    snapshot_count = db.execute(
        select(func.count())
        .select_from(ParticipantFeedbackSnapshot)
        .where(ParticipantFeedbackSnapshot.participant_id.in_(participant_ids))
    ).scalar_one()
    assert snapshot_count == 0
    assert groq_called["value"] is False

    repeat = client.get(
        f"/v1/golden-vault/fake-users/batches/{batch_id}/credentials",
        headers=vault_headers(),
    )
    assert repeat.status_code == 410


def test_generate_idempotency(client: TestClient, vault_env):
    key = str(uuid4())
    body = {
        "total": 1,
        "start_date": "2026-01-01",
        "daily": 1,
        "weekly": 0,
        "two_days": 0,
        "four_days": 0,
        "idempotency_key": key,
    }
    first = client.post("/v1/golden-vault/fake-users/generate", json=body, headers=vault_headers())
    second = client.post("/v1/golden-vault/fake-users/generate", json=body, headers=vault_headers())
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["batchId"] == second.json()["batchId"]


def test_synthetic_batch_filter_lists_only_batch_members(client: TestClient, db: Session, vault_env):
    body = {
        "total": 2,
        "start_date": "2026-01-02",
        "daily": 2,
        "weekly": 0,
        "two_days": 0,
        "four_days": 0,
        "idempotency_key": str(uuid4()),
    }
    summary = _run_batch(client, body)
    batch_id = summary["batchId"]
    listed = client.get(
        f"/v1/golden-vault/participants?synthetic_batch_id={batch_id}",
        headers=vault_headers(),
    )
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["total"] == 2
    overrides = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.synthetic_batch_id == batch_id)
    ).scalars().all()
    assert len(overrides) == 2
    assert all(row.is_synthetic_generated for row in overrides)


def test_fake_users_visible_on_researcher_dashboard(client: TestClient, db: Session, vault_env, researcher: Researcher):
    body = {
        "total": 1,
        "start_date": "2026-01-03",
        "daily": 1,
        "weekly": 0,
        "two_days": 0,
        "four_days": 0,
        "idempotency_key": str(uuid4()),
    }
    summary = _run_batch(client, body)
    creds = client.get(
        f"/v1/golden-vault/fake-users/batches/{summary['batchId']}/credentials",
        headers=vault_headers(),
    ).json()["credentials"]
    public_id = creds[0]["publicId"]
    dash = client.get("/v1/research/dashboard/participants", headers=researcher_headers(researcher))
    ids = [item["participantId"] for item in dash.json()["items"]]
    assert public_id in ids
    match = next(item for item in dash.json()["items"] if item["participantId"] == public_id)
    assert match.get("participantType") == "real"


def test_preview_schedule_distribution_service(db: Session):
    data = preview_fake_users(
        db,
        total=10,
        start_date=__import__("datetime").date(2026, 1, 1),
        daily=3,
        weekly=2,
        two_days=3,
        four_days=2,
    )
    assert data["totalUsers"] == 10
    assert data["estimatedPdfCount"] == 10
