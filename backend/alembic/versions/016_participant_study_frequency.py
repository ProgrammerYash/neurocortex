"""Participant study schedule preference

Revision ID: 016_study_frequency
Revises: 015_participant_messages
Create Date: 2026-07-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_study_frequency"
down_revision: Union[str, None] = "015_participant_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participants",
        sa.Column("study_frequency", sa.String(length=32), nullable=True),
    )
    op.create_check_constraint(
        "ck_participants_study_frequency",
        "participants",
        "study_frequency IS NULL OR study_frequency IN "
        "('daily', 'twice_weekly', 'four_times_weekly', 'weekly')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_participants_study_frequency", "participants", type_="check")
    op.drop_column("participants", "study_frequency")
