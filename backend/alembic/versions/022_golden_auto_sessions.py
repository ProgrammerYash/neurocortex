"""Golden Vault auto sessions

Revision ID: 022_golden_auto_sessions
Revises: 021_golden_demo_overrides
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022_golden_auto_sessions"
down_revision: Union[str, None] = "021_golden_demo_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_session_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("next_auto_session_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("last_auto_session_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("last_auto_session_local_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_session_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_golden_demo_overrides_auto_session_enabled",
        "golden_demo_overrides",
        ["auto_session_enabled"],
    )
    op.create_index(
        "ix_golden_demo_overrides_next_auto_session_at",
        "golden_demo_overrides",
        ["next_auto_session_at"],
    )

    op.create_table(
        "golden_auto_session_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("local_session_date", sa.Date(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bonus_session_delta", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metrics_before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metrics_after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "participant_id",
            "local_session_date",
            name="uq_golden_auto_session_events_participant_local_date",
        ),
    )
    op.create_index(
        "ix_golden_auto_session_events_participant_id",
        "golden_auto_session_events",
        ["participant_id"],
    )
    op.create_index(
        "ix_golden_auto_session_events_local_session_date",
        "golden_auto_session_events",
        ["local_session_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_golden_auto_session_events_local_session_date", table_name="golden_auto_session_events")
    op.drop_index("ix_golden_auto_session_events_participant_id", table_name="golden_auto_session_events")
    op.drop_table("golden_auto_session_events")
    op.drop_index("ix_golden_demo_overrides_next_auto_session_at", table_name="golden_demo_overrides")
    op.drop_index("ix_golden_demo_overrides_auto_session_enabled", table_name="golden_demo_overrides")
    op.drop_column("golden_demo_overrides", "auto_session_updated_at")
    op.drop_column("golden_demo_overrides", "last_auto_session_local_date")
    op.drop_column("golden_demo_overrides", "last_auto_session_at")
    op.drop_column("golden_demo_overrides", "next_auto_session_at")
    op.drop_column("golden_demo_overrides", "auto_session_enabled")
