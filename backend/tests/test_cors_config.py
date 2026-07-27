"""CORS origin parsing and credentialed middleware behavior."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.config import (
    Settings,
    cors_middleware_options,
    effective_cors_origins,
    parse_cors_allowed_origins,
)
from app.main import app as main_app


def _cors_test_client(origins: list[str]) -> TestClient:
    test_app = FastAPI()

    @test_app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return TestClient(test_app)


def _preflight(client: TestClient, origin: str) -> str | None:
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    return response.headers.get("access-control-allow-origin")


def test_parse_cors_allowed_origins_trims_and_dedupes():
    raw = " https://a.vercel.app ,http://localhost:5173,http://localhost:5173 "
    assert parse_cors_allowed_origins(raw) == [
        "https://a.vercel.app",
        "http://localhost:5173",
    ]


def test_parse_cors_allowed_origins_drops_wildcard():
    assert parse_cors_allowed_origins("*,http://127.0.0.1:5173") == ["http://127.0.0.1:5173"]


def test_development_merges_localhost_and_configured_origins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://neurocortex-demo.vercel.app,http://localhost:5173",
    )
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
    )
    origins = effective_cors_origins(settings)
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "https://neurocortex-demo.vercel.app" in origins


def test_production_uses_only_configured_origins(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    vercel = "https://neurocortex-production.vercel.app"
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", f"{vercel},http://localhost:5173")
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
    )
    origins = effective_cors_origins(settings)
    assert origins == [vercel, "http://localhost:5173"]
    assert "http://127.0.0.1:5173" not in origins


def test_cors_middleware_options_never_uses_wildcard_origin():
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
        cors_allowed_origins="http://localhost:5173",
    )
    opts = cors_middleware_options(settings)
    assert opts["allow_credentials"] is True
    assert opts["allow_origins"] != ["*"]
    assert "*" not in opts["allow_origins"]


def test_main_app_cors_middleware_uses_explicit_origins_not_wildcard():
    allow_origins: list[str] | None = None
    for middleware in main_app.user_middleware:
        if middleware.cls is CORSMiddleware:
            allow_origins = middleware.kwargs.get("allow_origins")
            assert middleware.kwargs.get("allow_credentials") is True
            break
    assert allow_origins is not None
    assert allow_origins != ["*"]
    assert "*" not in allow_origins


def test_localhost_accepted_in_development_configuration(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
    )
    client = _cors_test_client(effective_cors_origins(settings))
    assert _preflight(client, "http://localhost:5173") == "http://localhost:5173"


def test_loopback_ip_accepted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
    )
    client = _cors_test_client(effective_cors_origins(settings))
    assert _preflight(client, "http://127.0.0.1:5173") == "http://127.0.0.1:5173"


def test_configured_vercel_origin_accepted(monkeypatch: pytest.MonkeyPatch):
    vercel = "https://neurocortex-app.vercel.app"
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", vercel)
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
    )
    client = _cors_test_client(effective_cors_origins(settings))
    assert _preflight(client, vercel) == vercel


def test_unknown_origin_not_allowed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://allowed.example.com")
    settings = Settings(
        database_url="postgresql+psycopg2://u:p@localhost:5432/db",
        jwt_secret="x" * 32,
    )
    client = _cors_test_client(effective_cors_origins(settings))
    assert _preflight(client, "https://evil.example.com") is None
