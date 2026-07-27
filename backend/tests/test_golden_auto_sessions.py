"""Golden Vault Auto Session (Phase 5G)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.daily_session import DailySession
from app.models.golden_auto_session_event import GoldenAutoSessionEvent
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.module_result import ModuleResult
from app.models.participant import Participant
from app.models.participant_feedback_snapshot import ParticipantFeedbackSnapshot
from app.services.golden_vault_auto_session_service import (
    AUTO_WINDOW_END_MINUTE,
    AUTO_WINDOW_START_MINUTE,
    compute_initial_next_auto_session_at,
    process_due_golden_auto_sessions,
)
from app.services.golden_vault_service import (
    enable_override,
    list_vault_participants,
    run_bulk_action,
    set_auto_session_enabled,
)
from app.utils.security import create_golden_vault_access_token, hash_invite_code
from tests.test_electronic_consent import register
from tests.test_researcher_dashboard import participant_by_public_id, researcher


@pytest.fixture()
def vault_env(monkeypatch):
    monkeypatch.setenv("GOLDEN_VAULT_ENABLED", "true")
    monkeypatch.setenv("GOLDEN_VAULT_CODE_HASH", hash_invite_code(f"vault-{uuid4()}"))
    monkeypatch.setenv("GOLDEN_AUTO_SESSIONS_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def vault_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {create_golden_vault_access_token()}"}


def test_enable_auto_session_stores_future_time(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    set_auto_session_enabled(db, public_id=public_id, enabled=True)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    assert row.auto_session_enabled is True
    assert row.next_auto_session_at is not None
    assert row.next_auto_session_at > datetime.now(UTC)


def test_scheduled_time_within_afternoon_window(db: Session, vault_env, researcher: Researcher, client: TestClient):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    set_auto_session_enabled(db, public_id=public_id, enabled=True)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    tz = ZoneInfo(get_settings().study_timezone)
    local = row.next_auto_session_at.astimezone(tz)
    minute = local.hour * 60 + local.minute
    assert AUTO_WINDOW_START_MINUTE <= minute <= AUTO_WINDOW_END_MINUTE


def test_scheduled_time_persists(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    set_auto_session_enabled(db, public_id=public_id, enabled=True)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    first = row.next_auto_session_at
    db.refresh(row)
    second = row.next_auto_session_at
    assert first == second
    detail1 = client.get(f"/v1/golden-vault/participants/{public_id}", headers=vault_headers())
    detail2 = client.get(f"/v1/golden-vault/participants/{public_id}", headers=vault_headers())
    assert detail1.json()["nextAutoSessionAt"] == detail2.json()["nextAutoSessionAt"]


def test_processor_awards_one_bonus_session(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    set_auto_session_enabled(db, public_id=public_id, enabled=True)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    row.next_auto_session_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()
    before = int(row.bonus_sessions or 0)
    summary = process_due_golden_auto_sessions(db, batch_size=10)
    db.flush()
    db.refresh(row)
    assert summary["awarded"] >= 1
    assert int(row.bonus_sessions or 0) == before + 1


def test_processor_does_not_create_real_records(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    set_auto_session_enabled(db, public_id=public_id, enabled=True)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    row.next_auto_session_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()
    process_due_golden_auto_sessions(db)
    ds = db.execute(select(func.count()).select_from(DailySession).where(DailySession.participant_id == participant.id)).scalar_one()
    mr = db.execute(
        select(func.count()).select_from(ModuleResult).join(DailySession).where(DailySession.participant_id == participant.id)
    ).scalar_one()
    snaps = db.execute(
        select(func.count()).select_from(ParticipantFeedbackSnapshot).where(
            ParticipantFeedbackSnapshot.participant_id == participant.id
        )
    ).scalar_one()
    assert ds == 0 and mr == 0 and snaps == 0


def test_duplicate_local_date_not_awarded_twice(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    set_auto_session_enabled(db, public_id=public_id, enabled=True)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    row.next_auto_session_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()
    process_due_golden_auto_sessions(db)
    count_after_first = int(row.bonus_sessions or 0)
    row.next_auto_session_at = datetime.now(UTC) - timedelta(minutes=1)
    tz = ZoneInfo(get_settings().study_timezone)
    local_date = row.last_auto_session_local_date or datetime.now(tz).date()
    row.next_auto_session_at = compute_initial_next_auto_session_at(row, now=datetime.now(UTC))
    row.next_auto_session_at = datetime.now(UTC) - timedelta(minutes=1)
    db.flush()
    process_due_golden_auto_sessions(db)
    db.refresh(row)
    events = db.execute(
        select(func.count()).select_from(GoldenAutoSessionEvent).where(
            GoldenAutoSessionEvent.participant_id == participant.id,
            GoldenAutoSessionEvent.local_session_date == local_date,
        )
    ).scalar_one()
    assert events == 1
    assert int(row.bonus_sessions or 0) == count_after_first


def test_suspended_participant_hidden_from_vault_list(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    participant = participant_by_public_id(db, public_id)
    participant.is_suspended = True
    participant.suspended_until = datetime.now(UTC) + timedelta(days=7)
    db.flush()
    items, total = list_vault_participants(db, limit=50, offset=0, search=public_id, golden_enabled=None, feedback_filter=None)
    assert total == 0
    assert all(row["participantId"] != public_id for row in items)


def test_removed_participant_hidden_from_vault_list(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    participant = participant_by_public_id(db, public_id)
    participant.removed_at = datetime.now(UTC)
    db.flush()
    items, total = list_vault_participants(db, limit=50, offset=0, search=public_id, golden_enabled=None, feedback_filter=None)
    assert total == 0


def test_bulk_auto_session_enable(client: TestClient, db: Session, vault_env, researcher: Researcher):
    ids = [register(client).json()["public_id"] for _ in range(2)]
    for pid in ids:
        enable_override(db, public_id=pid)
    result = run_bulk_action(
        db,
        payload={"action": "auto_session_enable", "participant_public_ids": ids, "selection_mode": "explicit"},
    )
    assert result["succeeded_count"] == 2
    for pid in ids:
        participant = participant_by_public_id(db, pid)
        row = db.execute(
            select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
        ).scalar_one()
        assert row.auto_session_enabled is True


def test_api_patch_auto_session(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    response = client.patch(
        f"/v1/golden-vault/participants/{public_id}/auto-session",
        headers=vault_headers(),
        json={"enabled": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["autoSessionEnabled"] is True
    assert body["nextAutoSessionAt"]


def test_run_now_endpoint(client: TestClient, db: Session, vault_env, researcher: Researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    client.patch(f"/v1/golden-vault/participants/{public_id}/auto-session", headers=vault_headers(), json={"enabled": True})
    before = client.get(f"/v1/golden-vault/participants/{public_id}", headers=vault_headers()).json()["bonusSessions"]
    run = client.post(f"/v1/golden-vault/participants/{public_id}/auto-session/run-now", headers=vault_headers())
    assert run.status_code == 200
    after = client.get(f"/v1/golden-vault/participants/{public_id}", headers=vault_headers()).json()["bonusSessions"]
    assert after == before + 1


def test_dashboard_detail_still_exposes_is_demo_override(client: TestClient, db: Session, vault_env, researcher: Researcher):
    from tests.test_researcher_dashboard import researcher_headers

    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    detail = client.get(
        f"/v1/research/dashboard/participants/{public_id}",
        headers=researcher_headers(researcher),
    )
    assert detail.status_code == 200
    assert detail.json()["isDemoOverride"] is True
