"""Participant Groq feedback snapshots

Revision ID: 019_feedback_snapshots
Revises: 018_participant_age_max_26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "019_feedback_snapshots"
down_revision: Union[str, None] = "018_participant_age_max_26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "participant_feedback_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=True),
        sa.Column("headline", sa.String(length=120), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="groq"),
        sa.Column("provider_model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("generated_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_session_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_latest_session_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_released", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_participant_feedback_snapshots_participant_id",
        "participant_feedback_snapshots",
        ["participant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_participant_feedback_snapshots_participant_id", table_name="participant_feedback_snapshots")
    op.drop_table("participant_feedback_snapshots")
