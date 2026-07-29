from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GoldenDemoOverride(Base):
    __tablename__ = "golden_demo_overrides"
    __table_args__ = (UniqueConstraint("participant_id", name="uq_golden_demo_overrides_participant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    bonus_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    bonus_coins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    simulated_reaction_ms: Mapped[float | None] = mapped_column(nullable=True)
    simulated_stress: Mapped[float | None] = mapped_column(nullable=True)
    simulated_fatigue: Mapped[float | None] = mapped_column(nullable=True)
    simulated_sleep_hours: Mapped[float | None] = mapped_column(nullable=True)
    simulated_memory_percent: Mapped[float | None] = mapped_column(nullable=True)
    simulated_session_completion_percent: Mapped[float | None] = mapped_column(nullable=True)

    simulated_feedback_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    simulated_feedback_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    simulated_feedback_headline: Mapped[str | None] = mapped_column(String(120), nullable=True)
    simulated_feedback_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulated_feedback_factors_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    last_active_minute_of_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_auto_data_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_synthetic_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    synthetic_batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    auto_data_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_data_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_data_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    auto_data_weekdays_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    auto_data_configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_data_last_reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    auto_session_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    next_auto_session_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_auto_session_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_auto_session_local_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_session_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
