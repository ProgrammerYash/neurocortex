"""Participant exact age and study feedback settings

Revision ID: 017_age_feedback_settings
Revises: 016_study_frequency
Create Date: 2026-07-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_age_feedback_settings"
down_revision: Union[str, None] = "016_study_frequency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("participants", sa.Column("age_years", sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        "ck_participants_age_years",
        "participants",
        "age_years IS NULL OR (age_years >= 11 AND age_years <= 23)",
    )
    op.create_table(
        "study_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "participant_feedback_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("participant_feedback_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("participant_feedback_updated_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        sa.text(
            "INSERT INTO study_settings (id, participant_feedback_enabled) VALUES (1, false)",
        ),
    )


def downgrade() -> None:
    op.drop_table("study_settings")
    op.drop_constraint("ck_participants_age_years", "participants", type_="check")
    op.drop_column("participants", "age_years")
