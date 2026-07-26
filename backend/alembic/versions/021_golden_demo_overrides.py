"""Golden Vault demo overrides

Revision ID: 021_golden_demo_overrides
Revises: 020_feedback_generation_locks
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021_golden_demo_overrides"
down_revision: Union[str, None] = "020_feedback_generation_locks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "golden_demo_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("bonus_sessions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bonus_coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("simulated_reaction_ms", sa.Float(), nullable=True),
        sa.Column("simulated_stress", sa.Float(), nullable=True),
        sa.Column("simulated_fatigue", sa.Float(), nullable=True),
        sa.Column("simulated_sleep_hours", sa.Float(), nullable=True),
        sa.Column("simulated_memory_percent", sa.Float(), nullable=True),
        sa.Column("simulated_session_completion_percent", sa.Float(), nullable=True),
        sa.Column("simulated_feedback_status", sa.String(length=32), nullable=True),
        sa.Column("simulated_feedback_level", sa.String(length=16), nullable=True),
        sa.Column("simulated_feedback_headline", sa.String(length=120), nullable=True),
        sa.Column("simulated_feedback_summary", sa.Text(), nullable=True),
        sa.Column("simulated_feedback_factors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_active_minute_of_day", sa.Integer(), nullable=True),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", name="uq_golden_demo_overrides_participant_id"),
    )
    op.create_index("ix_golden_demo_overrides_participant_id", "golden_demo_overrides", ["participant_id"])


def downgrade() -> None:
    op.drop_index("ix_golden_demo_overrides_participant_id", table_name="golden_demo_overrides")
    op.drop_table("golden_demo_overrides")
