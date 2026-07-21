"""Secure generation and validation of immutable electronic-consent PDFs."""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops, ImageFile, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

try:
    import fitz
except ImportError:  # Python runtimes without a compatible PyMuPDF wheel use the safe fallback.
    fitz = None

from app.services.consent_content import (
    CONSENT_VERSION,
    DAILY_SURVEY_SNAPSHOT,
    EXPECTED_STATIC_VALUES,
    SURVEY_VERSION,
    TEMPLATE_PATH,
    current_consent_content,
    template_sha256,
)

MAX_SIGNATURE_BYTES = 1_000_000
MAX_SIGNATURE_DIMENSION = 2048
MAX_SIGNATURE_PIXELS = 4_000_000
PNG_PREFIX = "data:image/png;base64,"

REQUIRED_FIELDS = frozenset(
    {
        "Form 4 Student Researchers",
        "Form 4 IC Title of Project",
        "Form 4 Purpose of the Project",
        "Form 4 Participation Asks",
        "Form 4 Time Required",
        "Form 4 Potential Risks of Study",
        "Form 4 Benefits",
        "Form 4 Confidentiality Maintained",
        "Form 4 Questions Contact",
        "Form 4 Adult Sponsor Name",
        "Form 4 Adult Sponsor Phone/Email",
        "Form 4 AIC or MA Date Reviewed and Signed",
        "Form 4 Research Participant Printed Name",
        "Form 4 Parent Guardian Date Reviewed and Signed",
        "Form 4 Parent Guardian Printed Name",
        "Form 4 AIC Signature",
        "Form 4 Sample Signature 5",
    }
)

STUDENT_SIGNATURE_FIELD = "Form 4 AIC Signature"
GUARDIAN_SIGNATURE_FIELD = "Form 4 Sample Signature 5"
STUDY_TIMEZONE = ZoneInfo("America/New_York")


def pdf_signing_date(signed_at: datetime) -> str:
    """Format a UTC signing timestamp as MM/DD/YY in study local time."""
    if signed_at.tzinfo is None:
        signed_at = signed_at.replace(tzinfo=UTC)
    return signed_at.astimezone(STUDY_TIMEZONE).strftime("%m/%d/%y")


class ConsentPdfError(ValueError):
    pass


def validate_printed_name(value: str, label: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < 2 or len(cleaned) > 200:
        raise ConsentPdfError(f"{label} must be between 2 and 200 characters")
    if any(ord(char) < 32 for char in cleaned):
        raise ConsentPdfError(f"{label} contains invalid characters")
    if stringWidth(cleaned, "Helvetica", 7) > 230:
        raise ConsentPdfError(f"{label} is too long to fit the approved form")
    return cleaned


def validate_signature_png(data_url: str, label: str) -> bytes:
    if not isinstance(data_url, str) or not data_url.startswith(PNG_PREFIX):
        raise ConsentPdfError(f"{label} must be a PNG data URL")
    encoded = data_url[len(PNG_PREFIX) :]
    if not encoded or len(encoded) > ((MAX_SIGNATURE_BYTES + 2) // 3) * 4 + 4:
        raise ConsentPdfError(f"{label} is empty or too large")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ConsentPdfError(f"{label} is not valid base64 PNG data") from exc
    if len(raw) > MAX_SIGNATURE_BYTES or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ConsentPdfError(f"{label} is not a valid PNG")

    Image.MAX_IMAGE_PIXELS = MAX_SIGNATURE_PIXELS
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format != "PNG" or getattr(probe, "n_frames", 1) != 1:
                raise ConsentPdfError(f"{label} must be a single PNG image")
            probe.verify()
        with Image.open(io.BytesIO(raw)) as opened:
            width, height = opened.size
            if (
                width < 2
                or height < 2
                or width > MAX_SIGNATURE_DIMENSION
                or height > MAX_SIGNATURE_DIMENSION
                or width * height > MAX_SIGNATURE_PIXELS
            ):
                raise ConsentPdfError(f"{label} dimensions are not allowed")
            image = opened.convert("RGBA")
    except ConsentPdfError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ConsentPdfError(f"{label} is a malformed PNG") from exc

    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    composite = Image.alpha_composite(white, image).convert("L")
    ink = composite.point(lambda pixel: 255 if pixel < 245 else 0)
    bbox = ink.getbbox()
    if bbox is None:
        raise ConsentPdfError(f"{label} is blank")
    ink_pixels = sum(
        1
        for pixel in (
            ink.get_flattened_data() if hasattr(ink, "get_flattened_data") else ink.getdata()
        )
        if pixel
    )
    if ink_pixels < max(12, int(width * height * 0.00005)):
        raise ConsentPdfError(f"{label} does not contain enough visible ink")

    left, top, right, bottom = bbox
    padding = max(2, min(width, height) // 100)
    crop_box = (
        max(0, left - padding),
        max(0, top - padding),
        min(width, right + padding),
        min(height, bottom + padding),
    )
    normalized = image.crop(crop_box)
    output = io.BytesIO()
    normalized.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _appendix_pdf(generated_at: datetime) -> bytes:
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "ConsentAppendixTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=16,
    )
    body = ParagraphStyle(
        "ConsentAppendixBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )
    document = SimpleDocTemplate(
        output,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="NeuroCortex Survey/Questionnaire Appendix",
    )
    story = [
        Paragraph("NeuroCortex Survey/Questionnaire Appendix", title),
        Paragraph(f"<b>Consent version:</b> {CONSENT_VERSION}", body),
        Paragraph(f"<b>Survey version:</b> {SURVEY_VERSION}", body),
        Paragraph(
            f"<b>Generation date (UTC):</b> {generated_at.strftime('%m/%d/%Y')}",
            body,
        ),
        Spacer(1, 8),
        Paragraph(
            "Daily Wellbeing Survey — questions may appear in a different order. "
            "A participant may choose not to answer any specific question.",
            body,
        ),
    ]
    for index, item in enumerate(DAILY_SURVEY_SNAPSHOT, start=1):
        story.append(
            Paragraph(
                f"<b>{index}. {item['question']}</b><br/>"
                f"{item['instructions']}<br/>"
                f"<i>Response:</i> {item['response']}",
                body,
            )
        )
    document.build(story)
    return output.getvalue()


def _validate_signature_render(page: Any, rect: Any, label: str) -> None:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=rect, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    difference = ImageChops.difference(image, Image.new("RGB", image.size, "white")).convert("L")
    visible = sum(1 for pixel in difference.getdata() if pixel > 12)
    if visible < 12:
        raise ConsentPdfError(f"{label} was not rendered visibly")


def _reportlab_image_box(rect: list[float], image_bytes: bytes) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = rect
    with Image.open(io.BytesIO(image_bytes)) as image:
        width, height = image.size
    available_width = max(1.0, x1 - x0 - 2.4)
    available_height = max(1.0, y1 - y0 - 2.4)
    scale = min(available_width / width, available_height / height)
    drawn_width = width * scale
    drawn_height = height * scale
    return (
        x0 + (x1 - x0 - drawn_width) / 2,
        y0 + (y1 - y0 - drawn_height) / 2,
        drawn_width,
        drawn_height,
    )


def _generate_with_pypdf_reportlab(
    *,
    participant_name: str,
    guardian_name: str,
    student_png: bytes,
    guardian_png: bytes,
    participant_signed_at: datetime,
    guardian_signed_at: datetime,
) -> tuple[bytes, list[float], list[float]]:
    """Portable fallback for Python versions not supported by PyMuPDF."""
    reader = PdfReader(str(TEMPLATE_PATH))
    fields = reader.get_fields() or {}
    if len(fields) != 17 or set(fields) != REQUIRED_FIELDS:
        raise ConsentPdfError("Approved consent template fields do not match the required form")
    page = reader.pages[0]
    widgets: dict[str, list[float]] = {}
    for reference in page.get("/Annots") or []:
        annotation = reference.get_object()
        name = str(annotation.get("/T") or "")
        if name:
            widgets[name] = [float(value) for value in annotation.get("/Rect")]
    if set(widgets) != REQUIRED_FIELDS:
        raise ConsentPdfError("Approved consent template widgets do not match the required form")

    values = {
        **{field_name: str(fields[field_name].get("/V") or "") for field_name in REQUIRED_FIELDS},
        "Form 4 Research Participant Printed Name": participant_name,
        "Form 4 AIC or MA Date Reviewed and Signed": pdf_signing_date(participant_signed_at),
        "Form 4 Parent Guardian Printed Name": guardian_name,
        "Form 4 Parent Guardian Date Reviewed and Signed": pdf_signing_date(guardian_signed_at),
    }
    overlay_buffer = io.BytesIO()
    overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=letter, pageCompression=1)
    for field_name in REQUIRED_FIELDS - {STUDENT_SIGNATURE_FIELD, GUARDIAN_SIGNATURE_FIELD}:
        value = values[field_name]
        if not value:
            continue
        x0, y0, x1, y1 = widgets[field_name]
        font_size = min(10.0, max(5.0, (y1 - y0) * 0.62))
        while font_size > 5 and stringWidth(value, "Helvetica", font_size) > x1 - x0 - 3:
            font_size -= 0.25
        overlay_canvas.setFont("Helvetica", font_size)
        overlay_canvas.drawString(x0 + 1.5, y0 + max(1.0, ((y1 - y0) - font_size) / 2), value)
    for field_name, image_bytes in (
        (STUDENT_SIGNATURE_FIELD, student_png),
        (GUARDIAN_SIGNATURE_FIELD, guardian_png),
    ):
        x, y, width, height = _reportlab_image_box(widgets[field_name], image_bytes)
        overlay_canvas.drawImage(
            ImageReader(io.BytesIO(image_bytes)),
            x,
            y,
            width=width,
            height=height,
            preserveAspectRatio=True,
            mask="auto",
        )
    overlay_canvas.save()
    overlay_buffer.seek(0)
    writer = PdfWriter()
    writer.add_page(page)
    output_page = writer.pages[0]
    output_page.merge_page(PdfReader(overlay_buffer).pages[0])
    if NameObject("/Annots") in output_page:
        del output_page[NameObject("/Annots")]
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue(), widgets[STUDENT_SIGNATURE_FIELD], widgets[GUARDIAN_SIGNATURE_FIELD]


def generate_consent_pdf(
    *,
    participant_printed_name: str,
    guardian_printed_name: str,
    participant_signature_png: str,
    guardian_signature_png: str,
    participant_signed_at: datetime,
    guardian_signed_at: datetime,
) -> tuple[bytes, str]:
    participant_name = validate_printed_name(participant_printed_name, "Student printed name")
    guardian_name = validate_printed_name(guardian_printed_name, "Guardian printed name")
    student_png = validate_signature_png(participant_signature_png, "Student signature")
    guardian_png = validate_signature_png(guardian_signature_png, "Guardian signature")
    current_consent_content()
    template_sha256()

    try:
        final_pdf, student_rect, guardian_rect = _generate_with_pypdf_reportlab(
            participant_name=participant_name,
            guardian_name=guardian_name,
            student_png=student_png,
            guardian_png=guardian_png,
            participant_signed_at=participant_signed_at,
            guardian_signed_at=guardian_signed_at,
        )
    except ConsentPdfError:
        raise
    except Exception as exc:
        raise ConsentPdfError("Completed consent PDF could not be generated") from exc

    _validate_generated_pdf(
        final_pdf,
        participant_name=participant_name,
        guardian_name=guardian_name,
        participant_date=pdf_signing_date(participant_signed_at),
        guardian_date=pdf_signing_date(guardian_signed_at),
        student_rect=student_rect,
        guardian_rect=guardian_rect,
    )
    return final_pdf, hashlib.sha256(final_pdf).hexdigest()


def _validate_generated_pdf(
    pdf_bytes: bytes,
    *,
    participant_name: str,
    guardian_name: str,
    participant_date: str,
    guardian_date: str,
    student_rect: Any,
    guardian_rect: Any,
) -> None:
    if not pdf_bytes.startswith(b"%PDF"):
        raise ConsentPdfError("Completed consent output is not a valid PDF")
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) != 1:
            raise ConsentPdfError("Completed consent must be exactly one page")
        if reader.get_fields():
            raise ConsentPdfError("Completed consent PDF was not flattened")
        text = reader.pages[0].extract_text() or ""
        for expected in (
            participant_name,
            guardian_name,
            participant_date,
            guardian_date,
            EXPECTED_STATIC_VALUES["student_researcher"],
            "NeuroCortex",
        ):
            if expected not in text:
                raise ConsentPdfError("Completed consent PDF failed content validation")

        xobjects = reader.pages[0].get("/Resources", {}).get("/XObject", {})
        content = reader.pages[0].get_contents().get_data()
        image_draws = sum(
            content.count(f"/{str(name).lstrip('/')}".encode())
            for name in xobjects
        )
        if not xobjects or image_draws < 2:
            raise ConsentPdfError("Completed consent PDF is missing visible signatures")

        if fitz is not None:
            rendered = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                page = rendered[0]
                page_height = page.rect.height
                for rect, label in (
                    (student_rect, "Student signature"),
                    (guardian_rect, "Guardian signature"),
                ):
                    x0, y0, x1, y1 = rect
                    # AcroForm rectangles use bottom-left coordinates; PyMuPDF
                    # clipping uses top-left coordinates.
                    clip = fitz.Rect(x0, page_height - y1, x1, page_height - y0)
                    _validate_signature_render(page, clip, label)
            finally:
                rendered.close()
        else:
            import pypdfium2

            portable_document = pypdfium2.PdfDocument(pdf_bytes)
            try:
                rendered = portable_document[0].render(scale=3).to_pil().convert("RGB")
                for rect, label in (
                    (student_rect, "Student signature"),
                    (guardian_rect, "Guardian signature"),
                ):
                    x0, y0, x1, y1 = rect
                    crop = rendered.crop(
                        (
                            int(x0 * 3),
                            int((792 - y1) * 3),
                            int(x1 * 3),
                            int((792 - y0) * 3),
                        )
                    )
                    difference = ImageChops.difference(
                        crop,
                        Image.new("RGB", crop.size, "white"),
                    ).convert("L")
                    pixels = (
                        difference.get_flattened_data()
                        if hasattr(difference, "get_flattened_data")
                        else difference.getdata()
                    )
                    if sum(1 for pixel in pixels if pixel > 12) < 12:
                        raise ConsentPdfError(f"{label} was not rendered visibly")
            finally:
                portable_document.close()
    except ConsentPdfError:
        raise
    except Exception as exc:
        raise ConsentPdfError("Completed consent PDF failed validation") from exc


def delivery_pdf_bytes(stored_pdf_bytes: bytes) -> bytes:
    """Return a one-page consent PDF for researcher delivery without mutating storage."""
    if not stored_pdf_bytes.startswith(b"%PDF"):
        raise ConsentPdfError("Stored consent document is not a valid PDF")
    reader = PdfReader(io.BytesIO(stored_pdf_bytes))
    page_count = len(reader.pages)
    if page_count == 0:
        raise ConsentPdfError("Stored consent document has no pages")
    if page_count == 1:
        return stored_pdf_bytes
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    output = io.BytesIO()
    writer.write(output)
    delivery = output.getvalue()
    if not delivery.startswith(b"%PDF"):
        raise ConsentPdfError("One-page consent delivery PDF is invalid")
    delivery_reader = PdfReader(io.BytesIO(delivery))
    if len(delivery_reader.pages) != 1:
        raise ConsentPdfError("One-page consent delivery PDF is invalid")
    return delivery
