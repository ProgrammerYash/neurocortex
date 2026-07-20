import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.participant import Participant


class ConsentRecord(Base):
    """Immutable completed electronic consent document."""

    __tablename__ = "consent_records"
    __table_args__ = (
        UniqueConstraint(
            "participant_id",
            "consent_version",
            name="uq_consent_records_participant_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    participant_printed_name: Mapped[str] = mapped_column(String(200), nullable=False)
    guardian_printed_name: Mapped[str] = mapped_column(String(200), nullable=False)
    participant_signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    guardian_signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consent_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    survey_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        unique=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    participant: Mapped["Participant"] = relationship(back_populates="consent_records")


@event.listens_for(ConsentRecord, "before_update")
def prevent_completed_consent_mutation(_mapper, _connection, target: ConsentRecord) -> None:
    allowed = {"revoked_at", "revocation_reason"}
    state = inspect(target)
    changed = {
        attribute.key
        for attribute in state.attrs
        if attribute.key != "participant" and attribute.history.has_changes()
    }
    forbidden = changed - allowed
    if forbidden:
        raise ValueError("Completed consent records are immutable")
