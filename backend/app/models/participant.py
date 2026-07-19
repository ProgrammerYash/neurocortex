import uuid
from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.daily_session import DailySession
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
    age_consent_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pet_choice: Mapped[str] = mapped_column(String(32), nullable=False)
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
