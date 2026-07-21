"""Participant account management fields and audit log

Revision ID: 014_participant_account
Revises: 013_electronic_consent
Create Date: 2026-07-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014_participant_account"
down_revision: Union[str, None] = "013_electronic_consent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participants",
        sa.Column("is_suspended", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "participants",
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("suspended_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("suspension_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("is_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "participants",
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("disabled_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("removal_reason", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "participants",
        sa.Column("must_change_pin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "participants",
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "participant_account_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("researcher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("duration_code", sa.String(length=32), nullable=True),
        sa.Column("previous_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resulting_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["researcher_id"], ["researchers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_participant_account_actions_participant_id",
        "participant_account_actions",
        ["participant_id"],
    )
    op.create_index(
        "ix_participant_account_actions_created_at",
        "participant_account_actions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_participant_account_actions_created_at", table_name="participant_account_actions")
    op.drop_index("ix_participant_account_actions_participant_id", table_name="participant_account_actions")
    op.drop_table("participant_account_actions")
    op.drop_column("participants", "auth_version")
    op.drop_column("participants", "must_change_pin")
    op.drop_column("participants", "removal_reason")
    op.drop_column("participants", "removed_at")
    op.drop_column("participants", "disabled_reason")
    op.drop_column("participants", "disabled_at")
    op.drop_column("participants", "is_disabled")
    op.drop_column("participants", "suspension_reason")
    op.drop_column("participants", "suspended_until")
    op.drop_column("participants", "suspended_at")
    op.drop_column("participants", "is_suspended")
