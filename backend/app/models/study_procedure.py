import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.study_protocol import StudyProtocol


class StudyProcedureVersion(Base):
    __tablename__ = "study_procedure_versions"
    __table_args__ = (
        UniqueConstraint("version", name="uq_study_procedure_versions_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("study_protocols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    required_modules: Mapped[list] = mapped_column(JSONB, nullable=False)
    required_survey_questions: Mapped[list] = mapped_column(JSONB, nullable=False)
    min_session_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_session_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    max_sessions_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    min_minutes_between_sessions: Mapped[int] = mapped_column(Integer, nullable=False)
    study_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    study_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    participant_target: Mapped[int] = mapped_column(Integer, nullable=False)
    min_sessions_per_participant: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    protocol: Mapped["StudyProtocol"] = relationship()
