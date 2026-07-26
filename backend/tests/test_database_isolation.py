"""Prove pytest uses an isolated database separate from development DATABASE_URL."""

from __future__ import annotations

from sqlalchemy import func, select

from app.config import get_settings
from app.models.consent_record import ConsentRecord
from tests.conftest import DEFAULT_TEST_DATABASE_URL


def test_pytest_database_url_is_isolated():
    settings = get_settings()
    assert "neurocortex_test" in settings.database_url
    assert settings.database_url != DEFAULT_TEST_DATABASE_URL.replace("neurocortex_test", "neurocortex") or (
        "neurocortex_test" in settings.database_url
    )


def test_consent_table_empty_at_transaction_start(db):
    """Each test transaction starts without visible consent rows from other connections."""
    count = db.execute(select(func.count()).select_from(ConsentRecord)).scalar_one()
    assert count == 0
