"""Seal one-time fake-user credential payloads

Revision ID: 025_fake_user_credentials
Revises: 024_typed_synthetic_users
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025_fake_user_credentials"
down_revision: Union[str, None] = "024_typed_synthetic_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "golden_fake_user_batches",
        sa.Column("credentials_sealed", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("golden_fake_user_batches", "credentials_sealed")
