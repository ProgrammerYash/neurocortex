"""Initial participants table

Revision ID: 001_initial_participants
Revises:
Create Date: 2026-07-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_participants"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("pin_hash", sa.String(length=255), nullable=False),
        sa.Column("grade", sa.String(length=64), nullable=False),
        sa.Column("age_range", sa.String(length=32), nullable=False),
        sa.Column("pet_choice", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_participants_public_id", "participants", ["public_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_participants_public_id", table_name="participants")
    op.drop_table("participants")
