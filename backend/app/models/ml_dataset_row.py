import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.daily_session import DailySession
    from app.models.ml_dataset import MLDataset
    from app.models.participant import Participant


class MLDatasetRow(Base):
    __tablename__ = "ml_dataset_rows"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "participant_id",
            "session_date",
            name="uq_ml_dataset_rows_dataset_participant_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ml_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    public_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("daily_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quality_flags: Mapped[dict] = mapped_column(JSONB, nullable=False)
    exclusion_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    labels: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    dataset: Mapped["MLDataset"] = relationship(back_populates="rows")
    participant: Mapped["Participant"] = relationship()
    session: Mapped["DailySession | None"] = relationship()
