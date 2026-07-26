"""Shared pytest database isolation against a disposable test database."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg2://neurocortex:neurocortex@localhost:5432/neurocortex_test"
)


def _test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def _ensure_test_database_exists(url: str) -> None:
    parsed = make_url(url)
    db_name = parsed.database
    if not db_name or db_name == "postgres":
        return
    admin_url = parsed.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


def _run_migrations(database_url: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )


def _rebind_app_engine(database_url: str) -> Engine:
    from app.config import get_settings
    import app.database as database

    get_settings.cache_clear()
    database.engine.dispose()
    database.engine = create_engine(database_url, pool_pre_ping=True)
    database.SessionLocal = sessionmaker(
        bind=database.engine,
        autocommit=False,
        autoflush=False,
    )
    return database.engine


def pytest_configure(config: pytest.Config) -> None:
    test_url = _test_database_url()
    os.environ["DATABASE_URL"] = test_url
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-neurocortex-pytest-suite-key")
    os.environ.setdefault("ENVIRONMENT", "development")


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database() -> Generator[None, None, None]:
    test_url = _test_database_url()
    _ensure_test_database_exists(test_url)
    _run_migrations(test_url)
    engine = _rebind_app_engine(test_url)
    yield
    engine.dispose()


def _patch_commit_to_flush(session: Session) -> None:
    def commit_as_flush() -> None:
        session.flush()

    session.commit = commit_as_flush  # type: ignore[method-assign]


@pytest.fixture()
def db(isolated_test_database) -> Generator[Session, None, None]:
    from app.database import engine

    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    _patch_commit_to_flush(session)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    from app.database import get_db
    from app.main import app

    def override_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
