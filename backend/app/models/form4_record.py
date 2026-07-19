import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.generated_study_document import GeneratedStudyDocument


class Form4Record(Base):
    __tablename__ = "form4_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("generated_study_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    student_researcher_names: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    adult_sponsor: Mapped[str | None] = mapped_column(Text, nullable=True)
    adult_sponsor_contact: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_plan_submitted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    surveys_attached: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    published_instruments_legally_obtained: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    informed_consent_attached: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    qualified_scientist: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    full_committee_review: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    qualified_scientist_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    risk_assessment_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    minor_assent_required: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parental_permission_required: Mapped[str | None] = mapped_column(String(32), nullable=True)
    adult_informed_consent_required: Mapped[str | None] = mapped_column(String(32), nullable=True)
    signer_records: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
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

    document: Mapped["GeneratedStudyDocument"] = relationship(back_populates="form4_record")
