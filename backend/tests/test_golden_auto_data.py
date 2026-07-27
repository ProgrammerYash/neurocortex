"""Golden Vault Auto Data (Phase 5H)."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.daily_session import DailySession
from app.models.golden_auto_session_event import GoldenAutoSessionEvent
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.module_result import ModuleResult
from app.services.golden_vault_auto_data_service import (
    compute_auto_data_preview,
    iter_scheduled_dates,
    validate_auto_data_config,
)
from app.services.golden_vault_display_service import resolve_participant_display_metrics
from app.services.golden_vault_service import (
    GoldenVaultError,
    add_bonus_coins,
    add_bonus_sessions,
    apply_auto_data_for_public_id,
    delete_bonus_sessions,
    enable_override,
    preview_auto_data_for_public_id,
)
from app.services.researcher_dashboard_service import get_dashboard_summary
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


def test_daily_schedule_count_two_years():
    start = date(2024, 1, 1)
    end = date(2025, 12, 31)
    days = list(
        iter_scheduled_dates(
            start_date=start,
            end_date=end,
            frequency="daily",
            weekdays=list(range(7)),
            through_local=end,
        )
    )
    assert len(days) == 731


def test_preview_creates_no_events(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    participant = participant_by_public_id(db, public_id)
    before = db.execute(select(func.count()).select_from(GoldenAutoSessionEvent)).scalar_one()
    preview_auto_data_for_public_id(
        db,
        public_id=public_id,
        payload={"start_date": "2024-06-01", "end_date": None, "frequency": "daily"},
    )
    after = db.execute(select(func.count()).select_from(GoldenAutoSessionEvent)).scalar_one()
    assert before == after


def test_coin_grant_does_not_set_auto_data_user(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    add_bonus_coins(db, public_id=public_id, amount=50)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    assert row.is_auto_data_user is False


def test_manual_sessions_do_not_set_auto_data_user(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    add_bonus_sessions(db, public_id=public_id, amount=10)
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    assert row.is_auto_data_user is False


def test_apply_auto_data_sets_flag_and_idempotent(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    start = (date.today() - timedelta(days=14)).isoformat()
    apply_auto_data_for_public_id(
        db,
        public_id=public_id,
        payload={"start_date": start, "end_date": None, "frequency": "daily"},
    )
    participant = participant_by_public_id(db, public_id)
    row = db.execute(
        select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
    ).scalar_one()
    assert row.is_auto_data_user is True
    count1 = db.execute(
        select(func.count()).where(GoldenAutoSessionEvent.participant_id == participant.id)
    ).scalar_one()
    apply_auto_data_for_public_id(
        db,
        public_id=public_id,
        payload={"start_date": start, "end_date": None, "frequency": "daily"},
    )
    count2 = db.execute(
        select(func.count()).where(GoldenAutoSessionEvent.participant_id == participant.id)
    ).scalar_one()
    assert count2 == count1


def test_delete_sessions_rejects_over_bonus(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    add_bonus_sessions(db, public_id=public_id, amount=3)
    with pytest.raises(GoldenVaultError):
        delete_bonus_sessions(db, public_id=public_id, amount=10)


def test_no_daily_sessions_created_by_auto_data(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    participant = participant_by_public_id(db, public_id)
    ds_before = db.execute(
        select(func.count()).where(DailySession.participant_id == participant.id)
    ).scalar_one()
    apply_auto_data_for_public_id(
        db,
        public_id=public_id,
        payload={
            "start_date": (date.today() - timedelta(days=7)).isoformat(),
            "frequency": "daily",
        },
    )
    ds_after = db.execute(
        select(func.count()).where(DailySession.participant_id == participant.id)
    ).scalar_one()
    assert ds_after == ds_before


def test_dashboard_totals_consistent_with_manual_bonus(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    add_bonus_sessions(db, public_id=public_id, amount=50)
    summary = get_dashboard_summary(db)
    assert summary["totalSessions"] == summary["totalCompletedSessions"]


def test_auto_data_user_display_excludes_real_sessions(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    participant = participant_by_public_id(db, public_id)
    row = GoldenDemoOverride(participant_id=participant.id, enabled=True, bonus_sessions=5, is_auto_data_user=True)
    db.add(row)
    db.flush()
    display = resolve_participant_display_metrics(
        participant=participant,
        real_metrics={"sessions_completed": 20, "sessions_started": 20},
        golden_override=row,
    )
    assert display["displayedCompletedSessions"] == 5


def test_auto_data_preview_api(client: TestClient, db: Session, vault_env, researcher):
    public_id = register(client).json()["public_id"]
    enable_override(db, public_id=public_id)
    res = client.post(
        f"/v1/golden-vault/participants/{public_id}/auto-data/preview",
        headers=vault_headers(),
        json={"start_date": "2024-01-01", "end_date": None, "frequency": "daily"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["scheduledThroughToday"] >= 1
    assert body["newSessionsToAdd"] >= 0
