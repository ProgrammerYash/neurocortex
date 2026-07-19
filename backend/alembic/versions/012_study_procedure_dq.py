"""Study procedure, session protocol enforcement, and data quality flags

Revision ID: 012_study_procedure
Revises: 011_consent_category
Create Date: 2026-07-19

"""

import json
from datetime import UTC, date, datetime
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_study_procedure"
down_revision: Union[str, None] = "011_consent_category"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROCEDURE_ID = uuid4()
NOW = datetime.now(UTC)
REQUIRED_MODULES = ["reaction", "typing", "memory", "attention", "survey"]
REQUIRED_SURVEY = [
    "stress",
    "fatigue",
    "motivation",
    "mood",
    "sleep",
    "study",
    "homework",
    "exam",
    "socialStress",
    "physicalActivity",
]


def upgrade() -> None:
    op.create_table(
        "study_procedure_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("protocol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("required_modules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_survey_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("min_session_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("max_session_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("max_sessions_per_day", sa.Integer(), nullable=False),
        sa.Column("min_minutes_between_sessions", sa.Integer(), nullable=False),
        sa.Column("study_start_date", sa.Date(), nullable=False),
        sa.Column("study_end_date", sa.Date(), nullable=False),
        sa.Column("participant_target", sa.Integer(), nullable=False),
        sa.Column("min_sessions_per_participant", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["protocol_id"], ["study_protocols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_study_procedure_versions_version"),
    )
    op.create_index("ix_study_procedure_versions_protocol_id", "study_procedure_versions", ["protocol_id"])
    op.create_index("ix_study_procedure_versions_version", "study_procedure_versions", ["version"])

    op.execute(
        sa.text(
            """
            INSERT INTO study_procedure_versions (
                id, protocol_id, version, active, required_modules, required_survey_questions,
                min_session_duration_seconds, max_session_duration_seconds, max_sessions_per_day,
                min_minutes_between_sessions, study_start_date, study_end_date,
                participant_target, min_sessions_per_participant, effective_at, created_at
            )
            SELECT
                :procedure_id,
                sp.id,
                '2026-pilot-procedure-v1',
                true,
                CAST(:required_modules AS jsonb),
                CAST(:required_survey AS jsonb),
                60,
                900,
                1,
                720,
                CAST('2026-07-01' AS date),
                CAST('2026-12-31' AS date),
                30,
                14,
                :now,
                :now
            FROM study_protocols sp
            WHERE sp.version = '2026-pilot-v1'
            LIMIT 1
            """
        ).bindparams(
            procedure_id=PROCEDURE_ID,
            required_modules=json.dumps(REQUIRED_MODULES),
            required_survey=json.dumps(REQUIRED_SURVEY),
            now=NOW,
        )
    )

    op.add_column("daily_sessions", sa.Column("session_slot", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "daily_sessions",
        sa.Column("status", sa.String(length=32), server_default="in_progress", nullable=False),
    )
    op.add_column("daily_sessions", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("daily_sessions", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("daily_sessions", sa.Column("procedure_version", sa.String(length=64), nullable=True))
    op.add_column("daily_sessions", sa.Column("abandoned_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE daily_sessions
        SET status = CASE WHEN complete THEN 'complete' ELSE 'in_progress' END,
            started_at = COALESCE(started_at, created_at),
            completed_at = CASE WHEN complete THEN updated_at ELSE NULL END,
            procedure_version = '2026-pilot-procedure-v1'
        """
    )

    op.drop_constraint("uq_daily_sessions_participant_date", "daily_sessions", type_="unique")
    op.create_unique_constraint(
        "uq_daily_sessions_participant_date_slot",
        "daily_sessions",
        ["participant_id", "session_date", "session_slot"],
    )

    op.create_table(
        "session_data_quality_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("module_key", sa.String(length=32), nullable=True),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=32),
            server_default="unresolved",
            nullable=False,
        ),
        sa.Column("reviewed_by_researcher_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reviewed_by_researcher_id"], ["researchers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["daily_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_data_quality_flags_session_id", "session_data_quality_flags", ["session_id"])
    op.create_index("ix_session_data_quality_flags_flag_type", "session_data_quality_flags", ["flag_type"])
    op.create_index("ix_session_data_quality_flags_review_status", "session_data_quality_flags", ["review_status"])

    op.add_column(
        "ml_datasets",
        sa.Column("dataset_mode", sa.String(length=32), server_default="strict", nullable=False),
    )
    op.add_column("ml_dataset_rows", sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ml_dataset_rows", sa.Column("exclusion_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_foreign_key(
        "fk_ml_dataset_rows_session_id",
        "ml_dataset_rows",
        "daily_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ml_dataset_rows_session_id", "ml_dataset_rows", type_="foreignkey")
    op.drop_column("ml_dataset_rows", "exclusion_reasons")
    op.drop_column("ml_dataset_rows", "session_id")
    op.drop_column("ml_datasets", "dataset_mode")
    op.drop_table("session_data_quality_flags")
    op.drop_constraint("uq_daily_sessions_participant_date_slot", "daily_sessions", type_="unique")
    op.create_unique_constraint(
        "uq_daily_sessions_participant_date",
        "daily_sessions",
        ["participant_id", "session_date"],
    )
    op.drop_column("daily_sessions", "abandoned_at")
    op.drop_column("daily_sessions", "procedure_version")
    op.drop_column("daily_sessions", "completed_at")
    op.drop_column("daily_sessions", "started_at")
    op.drop_column("daily_sessions", "status")
    op.drop_column("daily_sessions", "session_slot")
    op.drop_table("study_procedure_versions")
