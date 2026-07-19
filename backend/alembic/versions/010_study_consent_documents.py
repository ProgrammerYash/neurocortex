"""Study consent, documents, and audit tables

Revision ID: 010_study_consent_documents
Revises: 009_ml_explanations
Create Date: 2026-07-19

"""

from datetime import UTC, datetime
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_study_consent_documents"
down_revision: Union[str, None] = "009_ml_explanations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROTOCOL_ID = uuid4()
ASSENT_FORM_ID = uuid4()
PARENTAL_FORM_ID = uuid4()
ADULT_FORM_ID = uuid4()
NOW = datetime.now(UTC)


def upgrade() -> None:
    op.create_table(
        "study_protocols",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_study_protocols_version"),
    )
    op.create_index("ix_study_protocols_version", "study_protocols", ["version"])

    op.create_table(
        "consent_form_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("protocol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("form_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["protocol_id"], ["study_protocols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consent_form_versions_protocol_id", "consent_form_versions", ["protocol_id"])
    op.create_index("ix_consent_form_versions_form_type", "consent_form_versions", ["form_type"])

    op.create_table(
        "participant_consent_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("protocol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_form_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recorded_by", sa.String(length=32), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["consent_form_version_id"], ["consent_form_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["protocol_id"], ["study_protocols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_participant_consent_events_participant_id", "participant_consent_events", ["participant_id"])
    op.create_index("ix_participant_consent_events_protocol_id", "participant_consent_events", ["protocol_id"])
    op.create_index("ix_participant_consent_events_event_type", "participant_consent_events", ["event_type"])
    op.create_index("ix_participant_consent_events_created_at", "participant_consent_events", ["created_at"])

    op.create_table(
        "generated_study_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("protocol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("artifact_path", sa.String(length=512), nullable=True),
        sa.Column("artifact_hash", sa.String(length=128), nullable=True),
        sa.Column("generated_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["generated_by_researcher_id"], ["researchers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["protocol_id"], ["study_protocols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_study_documents_document_type", "generated_study_documents", ["document_type"])
    op.create_index("ix_generated_study_documents_protocol_id", "generated_study_documents", ["protocol_id"])

    op.create_table(
        "form4_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_researcher_names", sa.Text(), nullable=True),
        sa.Column("project_title", sa.Text(), nullable=True),
        sa.Column("adult_sponsor", sa.Text(), nullable=True),
        sa.Column("adult_sponsor_contact", sa.Text(), nullable=True),
        sa.Column("research_plan_submitted", sa.Boolean(), nullable=True),
        sa.Column("surveys_attached", sa.Boolean(), nullable=True),
        sa.Column("published_instruments_legally_obtained", sa.Boolean(), nullable=True),
        sa.Column("informed_consent_attached", sa.Boolean(), nullable=True),
        sa.Column("qualified_scientist", sa.Boolean(), nullable=True),
        sa.Column("full_committee_review", sa.Boolean(), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("qualified_scientist_required", sa.Boolean(), nullable=True),
        sa.Column("risk_assessment_required", sa.Boolean(), nullable=True),
        sa.Column("minor_assent_required", sa.String(length=32), nullable=True),
        sa.Column("parental_permission_required", sa.String(length=32), nullable=True),
        sa.Column("adult_informed_consent_required", sa.String(length=32), nullable=True),
        sa.Column("signer_records", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["generated_study_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_form4_records_document_id"),
    )
    op.create_index("ix_form4_records_document_id", "form4_records", ["document_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_actor_type", "audit_events", ["actor_type"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_participant_id", "audit_events", ["participant_id"])
    op.create_index("ix_audit_events_document_id", "audit_events", ["document_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    study_protocols = sa.table(
        "study_protocols",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("version", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("effective_at", sa.DateTime(timezone=True)),
        sa.column("active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    consent_form_versions = sa.table(
        "consent_form_versions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("protocol_id", postgresql.UUID(as_uuid=True)),
        sa.column("form_type", sa.String()),
        sa.column("version", sa.String()),
        sa.column("content_hash", sa.String()),
        sa.column("effective_at", sa.DateTime(timezone=True)),
        sa.column("active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        study_protocols,
        [
            {
                "id": PROTOCOL_ID,
                "version": "2026-pilot-v1",
                "description": "NeuroCortex longitudinal cognitive research pilot protocol",
                "effective_at": NOW,
                "active": True,
                "created_at": NOW,
            }
        ],
    )
    op.bulk_insert(
        consent_form_versions,
        [
            {
                "id": ASSENT_FORM_ID,
                "protocol_id": PROTOCOL_ID,
                "form_type": "participant_assent",
                "version": "assent-v1",
                "content_hash": "sha256:pending-assent-v1",
                "effective_at": NOW,
                "active": True,
                "created_at": NOW,
            },
            {
                "id": PARENTAL_FORM_ID,
                "protocol_id": PROTOCOL_ID,
                "form_type": "parental_permission",
                "version": "parental-v1",
                "content_hash": "sha256:pending-parental-v1",
                "effective_at": NOW,
                "active": True,
                "created_at": NOW,
            },
            {
                "id": ADULT_FORM_ID,
                "protocol_id": PROTOCOL_ID,
                "form_type": "adult_informed_consent",
                "version": "adult-v1",
                "content_hash": "sha256:pending-adult-v1",
                "effective_at": NOW,
                "active": True,
                "created_at": NOW,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_document_id", table_name="audit_events")
    op.drop_index("ix_audit_events_participant_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_type", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_form4_records_document_id", table_name="form4_records")
    op.drop_table("form4_records")
    op.drop_index("ix_generated_study_documents_protocol_id", table_name="generated_study_documents")
    op.drop_index("ix_generated_study_documents_document_type", table_name="generated_study_documents")
    op.drop_table("generated_study_documents")
    op.drop_index("ix_participant_consent_events_created_at", table_name="participant_consent_events")
    op.drop_index("ix_participant_consent_events_event_type", table_name="participant_consent_events")
    op.drop_index("ix_participant_consent_events_protocol_id", table_name="participant_consent_events")
    op.drop_index("ix_participant_consent_events_participant_id", table_name="participant_consent_events")
    op.drop_table("participant_consent_events")
    op.drop_index("ix_consent_form_versions_form_type", table_name="consent_form_versions")
    op.drop_index("ix_consent_form_versions_protocol_id", table_name="consent_form_versions")
    op.drop_table("consent_form_versions")
    op.drop_index("ix_study_protocols_version", table_name="study_protocols")
    op.drop_table("study_protocols")
