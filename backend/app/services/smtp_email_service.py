"""SMTP email helpers for researcher bulk email."""

from __future__ import annotations

import smtplib
import time
from email.message import EmailMessage
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.audit_service import record_audit_event


def email_is_configured() -> bool:
    settings = get_settings()
    return bool(
        (settings.smtp_host or "").strip()
        and (settings.smtp_from_email or "").strip()
    )


def send_bulk_email(
    db: Session,
    *,
    public_ids: list[str],
    subject: str,
    body: str,
    researcher_id,
) -> dict[str, Any]:
    # No participant email field exists in the current schema.
    result = {
        "requested_count": len(public_ids),
        "eligible_count": 0,
        "succeeded_count": 0,
        "failed_count": 0,
        "skipped_count": len(public_ids),
        "failures": [{"public_id": pid, "message": "No contact email is available"} for pid in public_ids],
    }
    record_audit_event(
        db,
        actor_type="researcher",
        actor_id=researcher_id,
        event_type="bulk.email",
        metadata={"requested": len(public_ids), "skipped": len(public_ids)},
    )
    return result


def _send_single_email(*, recipient: str, subject: str, body: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    time.sleep(0.05)
