import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.module_result import ModuleResult
    from app.models.participant import Participant
    from app.models.session_data_quality_flag import SessionDataQualityFlag


SESSION_STATUS_IN_PROGRESS = "in_progress"
SESSION_STATUS_COMPLETE = "complete"
SESSION_STATUS_INCOMPLETE = "incomplete"
SESSION_STATUS_ABANDONED = "abandoned"

ACTIVE_SESSION_STATUSES = frozenset(
    {SESSION_STATUS_IN_PROGRESS, SESSION_STATUS_COMPLETE, SESSION_STATUS_INCOMPLETE}
)


class DailySession(Base):
    __tablename__ = "daily_sessions"
    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "session_date",
            "session_slot",
            name="uq_daily_sessions_participant_date_slot",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_slot: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SESSION_STATUS_IN_PROGRESS,
        server_default=SESSION_STATUS_IN_PROGRESS,
    )
    complete: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    procedure_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    participant: Mapped["Participant"] = relationship(back_populates="daily_sessions")
    module_results: Mapped[list["ModuleResult"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    data_quality_flags: Mapped[list["SessionDataQualityFlag"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
