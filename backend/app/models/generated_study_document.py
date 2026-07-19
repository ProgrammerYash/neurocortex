import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.form4_record import Form4Record
    from app.models.researcher import Researcher
    from app.models.study_protocol import StudyProtocol


class GeneratedStudyDocument(Base):
    __tablename__ = "generated_study_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    protocol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("study_protocols.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    artifact_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    artifact_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    generated_by_researcher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("researchers.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    protocol: Mapped["StudyProtocol"] = relationship()
    generated_by: Mapped["Researcher | None"] = relationship()
    form4_record: Mapped["Form4Record | None"] = relationship(back_populates="document", uselist=False)
