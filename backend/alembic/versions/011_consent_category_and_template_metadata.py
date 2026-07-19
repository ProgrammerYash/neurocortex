"""Consent category and template metadata

Revision ID: 011_consent_category
Revises: 010_study_consent_documents
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_consent_category"
down_revision: Union[str, None] = "010_study_consent_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "participants",
        sa.Column("age_consent_category", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_participants_age_consent_category", "participants", ["age_consent_category"])

    op.execute(
        """
        UPDATE participants
        SET age_consent_category = CASE
            WHEN age_range IN ('13-14', '15-16') THEN 'under_18'
            WHEN age_range IN ('19-20', '21-22', '23+') THEN 'age_18_or_over'
            WHEN age_range = '17-18' THEN 'unresolved'
            ELSE 'unresolved'
        END
        WHERE age_consent_category IS NULL
        """
    )

    op.add_column(
        "generated_study_documents",
        sa.Column("template_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "generated_study_documents",
        sa.Column("template_sha256", sa.String(length=64), nullable=True),
    )
    op.execute(
        """
        UPDATE generated_study_documents
        SET template_id = 'isef-human-participants-form4-2023-2024',
            template_sha256 = 'e53b2ef301b1cf665e3ea4f3a18b970b3fcd0f0d15baf926379e94b33337baeb'
        WHERE document_type = 'form_4' AND template_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("generated_study_documents", "template_sha256")
    op.drop_column("generated_study_documents", "template_id")
    op.drop_index("ix_participants_age_consent_category", table_name="participants")
    op.drop_column("participants", "age_consent_category")
