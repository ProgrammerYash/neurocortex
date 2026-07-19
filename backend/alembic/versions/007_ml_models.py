"""ML trained model metadata

Revision ID: 007_ml_models
Revises: 006_ml_dataset_labels
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_ml_models"
down_revision: Union[str, None] = "006_ml_dataset_labels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_type", sa.String(length=32), nullable=False),
        sa.Column("target_label", sa.String(length=64), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=16), nullable=False),
        sa.Column("label_schema_version", sa.String(length=16), nullable=True),
        sa.Column("model_version", sa.Integer(), nullable=False),
        sa.Column("train_size", sa.Integer(), nullable=False),
        sa.Column("validation_size", sa.Integer(), nullable=False),
        sa.Column("test_size", sa.Integer(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feature_importance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("artifact_path", sa.String(length=512), nullable=False),
        sa.Column("created_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_researcher_id"], ["researchers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dataset_id"], ["ml_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_models_dataset_id", "ml_models", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_ml_models_dataset_id", table_name="ml_models")
    op.drop_table("ml_models")
