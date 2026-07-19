"""Researchers and invite codes

Revision ID: 003_researchers
Revises: 002_daily_sessions
Create Date: 2026-07-19

"""

from typing import Sequence, Union
from uuid import uuid4

import bcrypt
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_researchers"
down_revision: Union[str, None] = "002_daily_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "researchers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "researcher_invites",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("researcher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["researcher_id"], ["researchers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_researcher_invites_researcher_id", "researcher_invites", ["researcher_id"])

    researcher_id = uuid4()
    code_hash = bcrypt.hashpw(b"yash gupta", bcrypt.gensalt()).decode("utf-8")
    op.execute(
        sa.text(
            """
            INSERT INTO researchers (id, display_name, email, password_hash, created_at)
            VALUES (:id, :display_name, NULL, NULL, now())
            """
        ).bindparams(id=researcher_id, display_name="Yash Gupta")
    )
    op.execute(
        sa.text(
            """
            INSERT INTO researcher_invites (id, code_hash, researcher_id, used_at, expires_at, created_at)
            VALUES (:id, :code_hash, :researcher_id, NULL, NULL, now())
            """
        ).bindparams(id=uuid4(), code_hash=code_hash, researcher_id=researcher_id)
    )


def downgrade() -> None:
    op.drop_index("ix_researcher_invites_researcher_id", table_name="researcher_invites")
    op.drop_table("researcher_invites")
    op.drop_table("researchers")
