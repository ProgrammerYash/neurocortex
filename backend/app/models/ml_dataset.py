import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.ml_dataset_artifact import MLDatasetArtifact
    from app.models.ml_dataset_row import MLDatasetRow
    from app.models.researcher import Researcher


class MLDataset(Base):
    __tablename__ = "ml_datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    date_range_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_range_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    label_schema_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    labels_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_researcher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("researchers.id", ondelete="SET NULL"),
        nullable=True,
    )
    dataset_mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="strict",
        server_default="strict",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    rows: Mapped[list["MLDatasetRow"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list["MLDatasetArtifact"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
    )
    created_by: Mapped["Researcher | None"] = relationship()
