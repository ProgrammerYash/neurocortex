"""Participant feedback generation locks

Revision ID: 020_feedback_generation_locks
Revises: 019_feedback_snapshots
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020_feedback_generation_locks"
down_revision: Union[str, None] = "019_feedback_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "participant_feedback_generation_locks",
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("participant_id"),
    )


def downgrade() -> None:
    op.drop_table("participant_feedback_generation_locks")
