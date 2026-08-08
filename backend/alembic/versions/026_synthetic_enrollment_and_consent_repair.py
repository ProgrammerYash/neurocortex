"""Synthetic enrollment timestamps and legacy consent delivery repair metadata.

Revision ID: 026_synth_consent_repair
Revises: 025_fake_user_credentials
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_synth_consent_repair"
down_revision: Union[str, None] = "025_fake_user_credentials"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "golden_demo_overrides",
        sa.Column("synthetic_enrollment_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("legacy_signature_repaired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("legacy_signature_repaired_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("legacy_signature_repair_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("repaired_delivery_pdf_bytes", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("repaired_delivery_pdf_sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consent_records", "repaired_delivery_pdf_sha256")
    op.drop_column("consent_records", "repaired_delivery_pdf_bytes")
    op.drop_column("consent_records", "legacy_signature_repair_version")
    op.drop_column("consent_records", "legacy_signature_repaired_by")
    op.drop_column("consent_records", "legacy_signature_repaired_at")
    op.drop_column("golden_demo_overrides", "synthetic_enrollment_at")
