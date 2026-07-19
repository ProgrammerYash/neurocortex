"""Append-only audit logging for consent and document workflows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def record_audit_event(
    db: Session,
    *,
    actor_type: str,
    event_type: str,
    actor_id: UUID | None = None,
    participant_id: UUID | None = None,
    document_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=uuid.uuid4(),
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        participant_id=participant_id,
        document_id=document_id,
        metadata_json=_sanitize_metadata(metadata or {}),
        created_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    blocked_keys = {"pin", "jwt", "token", "password", "signature", "pdf_bytes", "consent_text"}
    cleaned: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized = str(key).lower()
        if normalized in blocked_keys:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            cleaned[key] = value
        elif isinstance(value, dict):
            cleaned[key] = _sanitize_metadata(value)
        elif isinstance(value, list):
            cleaned[key] = [
                item if isinstance(item, (str, int, float, bool)) or item is None else str(item)
                for item in value
            ]
        else:
            cleaned[key] = str(value)
    return cleaned
