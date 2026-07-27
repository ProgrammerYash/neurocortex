"""Golden Vault auto data date ranges

Revision ID: 023_golden_auto_data_ranges
Revises: 022_golden_auto_sessions
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023_golden_auto_data_ranges"
down_revision: Union[str, None] = "022_golden_auto_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "golden_demo_overrides",
        sa.Column("is_auto_data_user", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_data_start_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_data_end_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_data_frequency", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_data_weekdays_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_data_configured_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "golden_demo_overrides",
        sa.Column("auto_data_last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_golden_demo_overrides_is_auto_data_user",
        "golden_demo_overrides",
        ["is_auto_data_user"],
    )

    # Backfill: auto session enabled => auto data user
    op.execute(
        sa.text(
            "UPDATE golden_demo_overrides SET is_auto_data_user = true WHERE auto_session_enabled = true"
        )
    )
    # Participants with at least one auto session event
    op.execute(
        sa.text(
            """
            UPDATE golden_demo_overrides g
            SET is_auto_data_user = true
            FROM (
                SELECT DISTINCT participant_id FROM golden_auto_session_events
            ) e
            WHERE g.participant_id = e.participant_id
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_golden_demo_overrides_is_auto_data_user", table_name="golden_demo_overrides")
    op.drop_column("golden_demo_overrides", "auto_data_last_reconciled_at")
    op.drop_column("golden_demo_overrides", "auto_data_configured_at")
    op.drop_column("golden_demo_overrides", "auto_data_weekdays_json")
    op.drop_column("golden_demo_overrides", "auto_data_frequency")
    op.drop_column("golden_demo_overrides", "auto_data_end_date")
    op.drop_column("golden_demo_overrides", "auto_data_start_date")
    op.drop_column("golden_demo_overrides", "is_auto_data_user")
