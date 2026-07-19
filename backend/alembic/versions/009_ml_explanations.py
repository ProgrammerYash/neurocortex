"""ML SHAP explanation records

Revision ID: 009_ml_explanations
Revises: 008_ml_predictions
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009_ml_explanations"
down_revision: Union[str, None] = "008_ml_predictions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["model_id"], ["ml_models.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["ml_predictions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id", name="uq_ml_explanations_prediction_id"),
    )
    op.create_index("ix_ml_explanations_prediction_id", "ml_explanations", ["prediction_id"])
    op.create_index("ix_ml_explanations_model_id", "ml_explanations", ["model_id"])
    op.create_index("ix_ml_explanations_participant_id", "ml_explanations", ["participant_id"])


def downgrade() -> None:
    op.drop_index("ix_ml_explanations_participant_id", table_name="ml_explanations")
    op.drop_index("ix_ml_explanations_model_id", table_name="ml_explanations")
    op.drop_index("ix_ml_explanations_prediction_id", table_name="ml_explanations")
    op.drop_table("ml_explanations")
