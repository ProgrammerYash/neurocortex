"""Expand participant age_years maximum to 26

Revision ID: 018_participant_age_max_26
Revises: 017_age_feedback_settings
Create Date: 2026-07-24

"""

from typing import Sequence, Union

from alembic import op

revision: str = "018_participant_age_max_26"
down_revision: Union[str, None] = "017_age_feedback_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_participants_age_years", "participants", type_="check")
    op.create_check_constraint(
        "ck_participants_age_years",
        "participants",
        "age_years IS NULL OR (age_years >= 11 AND age_years <= 26)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_participants_age_years", "participants", type_="check")
    op.create_check_constraint(
        "ck_participants_age_years",
        "participants",
        "age_years IS NULL OR (age_years >= 11 AND age_years <= 23)",
    )
