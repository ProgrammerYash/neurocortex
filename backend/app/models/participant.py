import uuid
from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.consent_record import ConsentRecord
    from app.models.daily_session import DailySession
    from app.models.participant_account_action import ParticipantAccountAction
    from app.models.participant_message import ParticipantMessage
    from app.models.participant_game_data import ParticipantGameData


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str] = mapped_column(String(64), nullable=False)
    age_range: Mapped[str] = mapped_column(String(32), nullable=False)
    age_years: Mapped[int | None] = mapped_column(nullable=True)
    age_consent_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pet_choice: Mapped[str] = mapped_column(String(32), nullable=False)
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removal_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    must_change_pin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    study_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    daily_sessions: Mapped[list["DailySession"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
    )
    game_data: Mapped["ParticipantGameData | None"] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
        uselist=False,
    )
    consent_records: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="participant",
        passive_deletes=True,
    )
    account_actions: Mapped[list["ParticipantAccountAction"]] = relationship(
        back_populates="participant",
        passive_deletes=True,
    )
    messages: Mapped[list["ParticipantMessage"]] = relationship(
        back_populates="participant",
        passive_deletes=True,
    )
