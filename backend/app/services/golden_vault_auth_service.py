"""Golden Vault authentication."""

from __future__ import annotations

from fastapi import Request

from app.config import get_settings
from app.services.audit_service import record_audit_event
from app.services.golden_vault_rate_limit import (
    check_golden_vault_login_allowed,
    record_golden_vault_login_failure,
    reset_golden_vault_login_attempts,
)
from app.utils.security import create_golden_vault_access_token, verify_invite_code
from sqlalchemy.orm import Session


class GoldenVaultAuthError(Exception):
    def __init__(self, message: str = "Invalid access code", status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def login_golden_vault(db: Session, *, code: str, request: Request) -> dict:
    settings = get_settings()
    client_key = _client_key(request)
    if not settings.golden_vault_enabled:
        record_golden_vault_login_failure(client_key)
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.login_failed",
            metadata={"reason": "disabled"},
        )
        db.rollback()
        raise GoldenVaultAuthError()

    if not check_golden_vault_login_allowed(client_key):
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.login_rate_limited",
            metadata={},
        )
        db.flush()
        raise GoldenVaultAuthError(status_code=429)

    code_hash = settings.golden_vault_code_hash
    if not code_hash or not verify_invite_code(code, code_hash):
        record_golden_vault_login_failure(client_key)
        record_audit_event(
            db,
            actor_type="golden_vault",
            event_type="golden_vault.login_failed",
            metadata={"reason": "invalid_code"},
        )
        db.rollback()
        raise GoldenVaultAuthError()

    reset_golden_vault_login_attempts(client_key)
    minutes = settings.golden_vault_token_minutes
    token = create_golden_vault_access_token(expires_minutes=minutes)
    record_audit_event(
        db,
        actor_type="golden_vault",
        event_type="golden_vault.login_success",
        metadata={},
    )
    db.flush()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": minutes * 60,
    }
