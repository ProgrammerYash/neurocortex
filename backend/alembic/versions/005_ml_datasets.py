"""ML dataset tables

Revision ID: 005_ml_datasets
Revises: 004_participant_game_data
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_ml_datasets"
down_revision: Union[str, None] = "004_participant_game_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=16), nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("participant_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("date_range_start", sa.Date(), nullable=True),
        sa.Column("date_range_end", sa.Date(), nullable=True),
        sa.Column("created_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_researcher_id"], ["researchers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ml_dataset_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", sa.String(length=32), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["ml_datasets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "participant_id",
            "session_date",
            name="uq_ml_dataset_rows_dataset_participant_date",
        ),
    )
    op.create_index("ix_ml_dataset_rows_dataset_id", "ml_dataset_rows", ["dataset_id"])
    op.create_index("ix_ml_dataset_rows_participant_id", "ml_dataset_rows", ["participant_id"])
    op.create_index("ix_ml_dataset_rows_public_id", "ml_dataset_rows", ["public_id"])
    op.create_index("ix_ml_dataset_rows_session_date", "ml_dataset_rows", ["session_date"])


def downgrade() -> None:
    op.drop_index("ix_ml_dataset_rows_session_date", table_name="ml_dataset_rows")
    op.drop_index("ix_ml_dataset_rows_public_id", table_name="ml_dataset_rows")
    op.drop_index("ix_ml_dataset_rows_participant_id", table_name="ml_dataset_rows")
    op.drop_index("ix_ml_dataset_rows_dataset_id", table_name="ml_dataset_rows")
    op.drop_table("ml_dataset_rows")
    op.drop_table("ml_datasets")
