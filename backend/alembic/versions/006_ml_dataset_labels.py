"""ML dataset labels and analysis artifacts

Revision ID: 006_ml_dataset_labels
Revises: 005_ml_datasets
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_ml_dataset_labels"
down_revision: Union[str, None] = "005_ml_datasets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ml_datasets",
        sa.Column("label_schema_version", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "ml_datasets",
        sa.Column("labels_generated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "ml_dataset_rows",
        sa.Column(
            "labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "ml_dataset_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("artifact_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dataset_id"], ["ml_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "artifact_type",
            "artifact_version",
            name="uq_ml_dataset_artifacts_dataset_type_version",
        ),
    )
    op.create_index(
        "ix_ml_dataset_artifacts_dataset_id",
        "ml_dataset_artifacts",
        ["dataset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ml_dataset_artifacts_dataset_id", table_name="ml_dataset_artifacts")
    op.drop_table("ml_dataset_artifacts")
    op.drop_column("ml_dataset_rows", "labels")
    op.drop_column("ml_datasets", "labels_generated_at")
    op.drop_column("ml_datasets", "label_schema_version")
