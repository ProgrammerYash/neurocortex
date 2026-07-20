"""Electronic consent records

Revision ID: 013_electronic_consent
Revises: 012_study_procedure
Create Date: 2026-07-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "013_electronic_consent"
down_revision: Union[str, None] = "012_study_procedure"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_printed_name", sa.String(length=200), nullable=False),
        sa.Column("guardian_printed_name", sa.String(length=200), nullable=False),
        sa.Column("participant_signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("guardian_signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_version", sa.String(length=64), nullable=False),
        sa.Column("survey_version", sa.String(length=64), nullable=False),
        sa.Column("template_sha256", sa.String(length=64), nullable=False),
        sa.Column("pdf_sha256", sa.String(length=64), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_consent_records_idempotency_key"),
        sa.UniqueConstraint(
            "participant_id",
            "consent_version",
            name="uq_consent_records_participant_version",
        ),
    )
    op.create_index("ix_consent_records_participant_id", "consent_records", ["participant_id"])
    op.create_index("ix_consent_records_consent_version", "consent_records", ["consent_version"])
    op.create_index("ix_consent_records_idempotency_key", "consent_records", ["idempotency_key"])
    op.create_index("ix_consent_records_created_at", "consent_records", ["created_at"])
    op.execute(
        """
        CREATE FUNCTION enforce_consent_record_immutability()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.participant_id IS DISTINCT FROM OLD.participant_id
               OR NEW.participant_printed_name IS DISTINCT FROM OLD.participant_printed_name
               OR NEW.guardian_printed_name IS DISTINCT FROM OLD.guardian_printed_name
               OR NEW.participant_signed_at IS DISTINCT FROM OLD.participant_signed_at
               OR NEW.guardian_signed_at IS DISTINCT FROM OLD.guardian_signed_at
               OR NEW.consent_version IS DISTINCT FROM OLD.consent_version
               OR NEW.survey_version IS DISTINCT FROM OLD.survey_version
               OR NEW.template_sha256 IS DISTINCT FROM OLD.template_sha256
               OR NEW.pdf_sha256 IS DISTINCT FROM OLD.pdf_sha256
               OR NEW.pdf_bytes IS DISTINCT FROM OLD.pdf_bytes
               OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
               OR NEW.created_at IS DISTINCT FROM OLD.created_at
            THEN
                RAISE EXCEPTION 'completed consent records are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER consent_records_immutable
        BEFORE UPDATE ON consent_records
        FOR EACH ROW EXECUTE FUNCTION enforce_consent_record_immutability()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS consent_records_immutable ON consent_records")
    op.execute("DROP FUNCTION IF EXISTS enforce_consent_record_immutability()")
    op.drop_index("ix_consent_records_created_at", table_name="consent_records")
    op.drop_index("ix_consent_records_idempotency_key", table_name="consent_records")
    op.drop_index("ix_consent_records_consent_version", table_name="consent_records")
    op.drop_index("ix_consent_records_participant_id", table_name="consent_records")
    op.drop_table("consent_records")
