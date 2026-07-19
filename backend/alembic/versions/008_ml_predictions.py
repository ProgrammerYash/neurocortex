"""ML prediction records

Revision ID: 008_ml_predictions
Revises: 007_ml_models
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_ml_predictions"
down_revision: Union[str, None] = "007_ml_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("prediction", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("features_used", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_id",
            "participant_id",
            "session_date",
            name="uq_ml_predictions_model_participant_date",
        ),
    )
    op.create_index("ix_ml_predictions_model_id", "ml_predictions", ["model_id"])
    op.create_index("ix_ml_predictions_participant_id", "ml_predictions", ["participant_id"])
    op.create_index("ix_ml_predictions_session_date", "ml_predictions", ["session_date"])


def downgrade() -> None:
    op.drop_index("ix_ml_predictions_session_date", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_participant_id", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_model_id", table_name="ml_predictions")
    op.drop_table("ml_predictions")
