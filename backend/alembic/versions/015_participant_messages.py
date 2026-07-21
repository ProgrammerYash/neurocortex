"""Participant inbox messages

Revision ID: 015_participant_messages
Revises: 014_participant_account
Create Date: 2026-07-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015_participant_messages"
down_revision: Union[str, None] = "014_participant_account"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "participant_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("researcher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(length=150), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["researcher_id"], ["researchers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_participant_messages_participant_id", "participant_messages", ["participant_id"])
    op.create_index("ix_participant_messages_created_at", "participant_messages", ["created_at"])
    op.create_index(
        "ix_participant_messages_unread",
        "participant_messages",
        ["participant_id", "read_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_participant_messages_unread", table_name="participant_messages")
    op.drop_index("ix_participant_messages_created_at", table_name="participant_messages")
    op.drop_index("ix_participant_messages_participant_id", table_name="participant_messages")
    op.drop_table("participant_messages")
