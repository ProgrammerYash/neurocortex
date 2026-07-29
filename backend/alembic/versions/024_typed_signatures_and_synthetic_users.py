"""Typed signatures and Golden Vault synthetic user batches

Revision ID: 024_typed_synthetic_users
Revises: 023_golden_auto_data_ranges
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024_typed_synthetic_users"
down_revision: Union[str, None] = "023_golden_auto_data_ranges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consent_records",
        sa.Column(
            "signature_method",
            sa.String(length=32),
            nullable=False,
            server_default="drawn_legacy",
        ),
    )
    op.add_column(
        "consent_records",
        sa.Column("participant_signature_text", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("guardian_signature_text", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("participant_agreed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column("guardian_agreed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "consent_records",
        sa.Column(
            "is_synthetic_demo_record",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "consent_records",
        sa.Column("synthetic_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_consent_records_synthetic_batch_id",
        "consent_records",
        ["synthetic_batch_id"],
        unique=False,
    )

    op.add_column(
        "golden_demo_overrides",
        sa.Column(
            "is_synthetic_generated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("synthetic_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_golden_demo_overrides_synthetic_batch_id",
        "golden_demo_overrides",
        ["synthetic_batch_id"],
        unique=False,
    )

    op.create_table(
        "golden_fake_user_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("daily_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weekly_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("two_days_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("four_days_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("successful_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("error_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("credentials_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_golden_fake_user_batches_idempotency_key",
        "golden_fake_user_batches",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_golden_fake_user_batches_status",
        "golden_fake_user_batches",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_golden_fake_user_batches_status", table_name="golden_fake_user_batches")
    op.drop_index("ix_golden_fake_user_batches_idempotency_key", table_name="golden_fake_user_batches")
    op.drop_table("golden_fake_user_batches")
    op.drop_index("ix_golden_demo_overrides_synthetic_batch_id", table_name="golden_demo_overrides")
    op.drop_column("golden_demo_overrides", "synthetic_batch_id")
    op.drop_column("golden_demo_overrides", "is_synthetic_generated")
    op.drop_index("ix_consent_records_synthetic_batch_id", table_name="consent_records")
    op.drop_column("consent_records", "synthetic_batch_id")
    op.drop_column("consent_records", "is_synthetic_demo_record")
    op.drop_column("consent_records", "guardian_agreed")
    op.drop_column("consent_records", "participant_agreed")
    op.drop_column("consent_records", "guardian_signature_text")
    op.drop_column("consent_records", "participant_signature_text")
    op.drop_column("consent_records", "signature_method")
