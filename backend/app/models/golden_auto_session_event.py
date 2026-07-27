from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GoldenAutoSessionEvent(Base):
    __tablename__ = "golden_auto_session_events"
    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "local_session_date",
            name="uq_golden_auto_session_events_participant_local_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bonus_session_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    metrics_before_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics_after_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
