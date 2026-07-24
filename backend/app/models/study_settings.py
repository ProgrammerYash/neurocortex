import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudySettings(Base):
    __tablename__ = "study_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    participant_feedback_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    participant_feedback_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    participant_feedback_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
