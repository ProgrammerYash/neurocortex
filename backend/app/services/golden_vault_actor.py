"""Resolve a stable researcher record for Golden Vault management audit trails."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.researcher import Researcher

_GOLDEN_VAULT_RESEARCHER_EMAIL = "golden-vault-system@neurocortex.internal"


def get_golden_vault_actor_researcher(db: Session) -> Researcher:
    researcher = db.execute(
        select(Researcher).where(Researcher.email == _GOLDEN_VAULT_RESEARCHER_EMAIL)
    ).scalar_one_or_none()
    if researcher is not None:
        return researcher
    researcher = Researcher(
        display_name="Golden Vault",
        email=_GOLDEN_VAULT_RESEARCHER_EMAIL,
        password_hash=None,
    )
    db.add(researcher)
    db.flush()
    return researcher
