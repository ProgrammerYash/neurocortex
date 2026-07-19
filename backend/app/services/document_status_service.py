"""Centralized Form 4 document status validation."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.models.form4_record import Form4Record
from app.models.generated_study_document import GeneratedStudyDocument

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"awaiting_irb", "void"}),
    "awaiting_irb": frozenset({"approved", "void", "superseded"}),
    "approved": frozenset({"superseded"}),
    "superseded": frozenset(),
    "void": frozenset(),
}

IRB_FIELDS = (
    "full_committee_review",
    "risk_level",
    "qualified_scientist_required",
    "risk_assessment_required",
    "minor_assent_required",
    "parental_permission_required",
    "adult_informed_consent_required",
)

REQUIRED_SIGNER_ROLES = (
    "Medical or Mental Health Professional",
    "Educator",
    "School Administrator",
)


class DocumentStatusError(Exception):
    def __init__(self, message: str, *, status_code: int = 422, error_code: str = "INVALID_STATUS_TRANSITION"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


def validate_status_transition(current: str, target: str) -> None:
    allowed = ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise DocumentStatusError(
            f"Cannot transition document status from '{current}' to '{target}'",
            error_code="INVALID_STATUS_TRANSITION",
        )


def _parse_approval_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise DocumentStatusError(
        f"Invalid approval date format: {value}",
        error_code="INVALID_APPROVAL_DATE",
    )


def validate_approved_requirements(record: Form4Record, *, approval_action_at: datetime | None = None) -> None:
    missing_irb = [field for field in IRB_FIELDS if getattr(record, field) in (None, "")]
    if missing_irb:
        raise DocumentStatusError(
            "All six IRB determinations must be answered before approval",
            error_code="IRB_FIELDS_INCOMPLETE",
        )

    signers = record.signer_records or []
    if len(signers) < 3:
        raise DocumentStatusError(
            "Three signer records are required before approval",
            error_code="SIGNERS_INCOMPLETE",
        )

    roles_present = {item.get("role") for item in signers if isinstance(item, dict)}
    missing_roles = [role for role in REQUIRED_SIGNER_ROLES if role not in roles_present]
    if missing_roles:
        raise DocumentStatusError(
            f"Missing required signer roles: {', '.join(missing_roles)}",
            error_code="SIGNERS_INCOMPLETE",
        )

    action_date = (approval_action_at or datetime.now(UTC)).date()
    for signer in signers:
        if not isinstance(signer, dict):
            raise DocumentStatusError("Signer records must be objects", error_code="SIGNERS_INCOMPLETE")
        if not signer.get("printed_name"):
            raise DocumentStatusError("Each signer must include a printed name", error_code="SIGNERS_INCOMPLETE")
        if not signer.get("degree_or_license"):
            raise DocumentStatusError(
                "Each signer must include a degree or professional license",
                error_code="SIGNERS_INCOMPLETE",
            )
        approval_date = _parse_approval_date(signer.get("approval_date"))
        if approval_date is None:
            raise DocumentStatusError("Each signer must include an approval date", error_code="SIGNERS_INCOMPLETE")
        if approval_date > action_date:
            raise DocumentStatusError(
                "Signer approval dates cannot be after the document approval action",
                error_code="INVALID_APPROVAL_DATE",
            )
        if signer.get("signature_status") == "signed":
            raise DocumentStatusError(
                "Digital signatures are not supported; use signature_status pending only",
                error_code="SIGNATURE_NOT_SUPPORTED",
            )


def validate_generate_transition(document: GeneratedStudyDocument) -> None:
    if document.status not in {"draft", "awaiting_irb"}:
        raise DocumentStatusError(
            "PDF generation is only allowed for draft or awaiting_irb documents",
            error_code="INVALID_STATUS_TRANSITION",
        )


def validate_status_update(
    document: GeneratedStudyDocument,
    record: Form4Record | None,
    *,
    target_status: str,
    confirm_approved: bool = False,
) -> None:
    validate_status_transition(document.status, target_status)
    if target_status == "approved":
        if not confirm_approved:
            raise DocumentStatusError(
                "Approval requires explicit confirmation",
                error_code="APPROVAL_CONFIRMATION_REQUIRED",
            )
        if record is None:
            raise DocumentStatusError("Form 4 record not found", status_code=404, error_code="NOT_FOUND")
        validate_approved_requirements(record)
