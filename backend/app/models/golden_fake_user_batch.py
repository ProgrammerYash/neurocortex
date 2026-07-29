from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GoldenFakeUserBatch(Base):
    __tablename__ = "golden_fake_user_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_count: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    weekly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    two_days_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    four_days_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    successful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True, index=True)
    error_summary_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    credentials_sealed: Mapped[str | None] = mapped_column(Text, nullable=True)
    credentials_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = ()
