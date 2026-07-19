"""Generate flattened ISEF Form 4 PDFs from the protected official template."""

from __future__ import annotations

import hashlib
import json
import os
from io import BytesIO
from pathlib import Path
from uuid import UUID

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.models.form4_record import Form4Record

BACKEND_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = BACKEND_ROOT / "templates"
DOCUMENTS_DIR = BACKEND_ROOT / "generated_documents"
TEMPLATE_PDF = TEMPLATES_DIR / "4-Human-Participants.pdf"
COORDINATES_FILE = TEMPLATES_DIR / "form4_coordinates.json"
METADATA_FILE = TEMPLATES_DIR / "form4_template_metadata.json"
OFFICIAL_TEMPLATE_SHA256 = "e53b2ef301b1cf665e3ea4f3a18b970b3fcd0f0d15baf926379e94b33337baeb"


class PdfFormError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def load_template_metadata() -> dict:
    if METADATA_FILE.exists():
        return json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    return {
        "template_id": "isef-human-participants-form4-2023-2024",
        "template_version": "isef-form4-2023-2024-official",
        "sha256": OFFICIAL_TEMPLATE_SHA256,
    }


def compute_template_sha256(path: Path | None = None) -> str:
    target = path or TEMPLATE_PDF
    return hashlib.sha256(target.read_bytes()).hexdigest()


def _load_coordinates() -> dict:
    if not COORDINATES_FILE.exists():
        raise PdfFormError("Form 4 coordinate map is missing")
    return json.loads(COORDINATES_FILE.read_text(encoding="utf-8"))


def _ensure_template(*, allow_dev_placeholder: bool = False) -> Path:
    settings = get_settings()
    if TEMPLATE_PDF.exists():
        actual_hash = compute_template_sha256()
        metadata = load_template_metadata()
        expected_hash = metadata.get("sha256", OFFICIAL_TEMPLATE_SHA256)
        if actual_hash.lower() != expected_hash.lower():
            if settings.study_mode in {"pilot", "production"}:
                raise PdfFormError(
                    "Official Form 4 template hash does not match expected metadata",
                    status_code=500,
                )
        if actual_hash.lower() == OFFICIAL_TEMPLATE_SHA256.lower():
            return TEMPLATE_PDF
        if settings.study_mode == "development" and allow_dev_placeholder:
            return TEMPLATE_PDF
        if settings.study_mode in {"pilot", "production"}:
            raise PdfFormError(
                "Official ISEF Form 4 template is required in pilot/production mode",
                status_code=500,
            )
        return TEMPLATE_PDF

    if settings.study_mode in {"pilot", "production"}:
        raise PdfFormError(
            "Official ISEF Form 4 template is missing. Place 4-Human-Participants.pdf in backend/templates/",
            status_code=500,
        )
    if allow_dev_placeholder or os.environ.get("ALLOW_FORM4_PLACEHOLDER") == "true":
        import importlib.util

        script_path = BACKEND_ROOT / "scripts" / "create_form4_template.py"
        spec = importlib.util.spec_from_file_location("create_form4_template", script_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.create_template(force=False)
    if not TEMPLATE_PDF.exists():
        raise PdfFormError(
            "Form 4 template PDF is missing. Place 4-Human-Participants.pdf in backend/templates/",
        )
    return TEMPLATE_PDF


def _checkbox_targets(record: Form4Record) -> dict[str, bool]:
    return {
        "research_plan_submitted": record.research_plan_submitted is True,
        "surveys_attached": record.surveys_attached is True,
        "published_instruments_legally_obtained": record.published_instruments_legally_obtained is True,
        "informed_consent_attached": record.informed_consent_attached is True,
        "qualified_scientist_yes": record.qualified_scientist is True,
        "qualified_scientist_no": record.qualified_scientist is False,
        "full_committee_review": record.full_committee_review is True,
        "risk_level_minimal": record.risk_level == "minimal",
        "risk_level_more_than_minimal": record.risk_level == "more_than_minimal",
        "qualified_scientist_required_yes": record.qualified_scientist_required is True,
        "qualified_scientist_required_no": record.qualified_scientist_required is False,
        "risk_assessment_required_yes": record.risk_assessment_required is True,
        "risk_assessment_required_no": record.risk_assessment_required is False,
        "minor_assent_required_yes": record.minor_assent_required == "yes",
        "minor_assent_required_no": record.minor_assent_required == "no",
        "minor_assent_required_na": record.minor_assent_required == "not_applicable",
        "parental_permission_required_yes": record.parental_permission_required == "yes",
        "parental_permission_required_no": record.parental_permission_required == "no",
        "parental_permission_required_na": record.parental_permission_required == "not_applicable",
        "adult_informed_consent_required_yes": record.adult_informed_consent_required == "yes",
        "adult_informed_consent_required_no": record.adult_informed_consent_required == "no",
        "adult_informed_consent_required_na": record.adult_informed_consent_required == "not_applicable",
    }


def _draw_wrapped_text(pdf: canvas.Canvas, text: str, x: float, y: float, *, size: int, max_width: float) -> None:
    pdf.setFont("Helvetica", size)
    words = str(text).split()
    line = ""
    cursor_y = y
    for word in words:
        candidate = f"{line} {word}".strip()
        if pdf.stringWidth(candidate, "Helvetica", size) <= max_width:
            line = candidate
        else:
            if line:
                pdf.drawString(x, cursor_y, line)
                cursor_y -= size + 2
            line = word
    if line:
        pdf.drawString(x, cursor_y, line)


def _build_overlay(record: Form4Record, coordinates: dict) -> bytes:
    packet = BytesIO()
    page_width, page_height = coordinates.get("page_size", [612, 792])
    pdf = canvas.Canvas(packet, pagesize=(page_width, page_height))

    for name, spec in coordinates.get("fields", {}).items():
        value = getattr(record, name, None)
        if value:
            max_width = spec.get("max_width", 220)
            _draw_wrapped_text(
                pdf,
                str(value),
                spec["x"],
                spec["y"],
                size=spec.get("size", 10),
                max_width=max_width,
            )

    checkbox_targets = _checkbox_targets(record)
    for name, spec in coordinates.get("checkboxes", {}).items():
        if checkbox_targets.get(name):
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(spec["x"], spec["y"], "X")

    signer_rows = coordinates.get("signer_rows", [])
    signers_by_role = {
        item.get("role"): item for item in (record.signer_records or []) if isinstance(item, dict)
    }
    for layout in signer_rows:
        signer = signers_by_role.get(layout["role"], {})
        for field in ("printed_name", "degree_or_license", "approval_date"):
            value = signer.get(field)
            if not value:
                continue
            spec = layout[field]
            pdf.setFont("Helvetica", spec.get("size", 8))
            pdf.drawString(spec["x"], spec["y"], str(value))

    pdf.save()
    packet.seek(0)
    return packet.read()


def generate_form4_pdf(document_id: UUID, record: Form4Record, *, allow_dev_placeholder: bool = False) -> tuple[Path, str]:
    template_path = _ensure_template(allow_dev_placeholder=allow_dev_placeholder)
    coordinates = _load_coordinates()
    overlay_bytes = _build_overlay(record, coordinates)

    reader = PdfReader(str(template_path))
    overlay_reader = PdfReader(BytesIO(overlay_bytes))
    writer = PdfWriter()

    for index, page in enumerate(reader.pages):
        if index < len(overlay_reader.pages):
            page.merge_page(overlay_reader.pages[index])
        writer.add_page(page)

    output_dir = DOCUMENTS_DIR / str(document_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "form-4.pdf"
    with output_path.open("wb") as handle:
        writer.write(handle)

    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return output_path, digest
