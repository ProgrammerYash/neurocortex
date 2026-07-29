"""Shared typed-signature typography for browser UI and PDF generation.

Uses ReportLab built-in Helvetica-Oblique (PDF-safe, no external font files).
Frontend uses a matching cursive system stack — no remote font requests.
"""

from __future__ import annotations

import io

from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

# CSS stack for React consent UI (local system cursive fonts only).
SIGNATURE_FONT_FAMILY_CSS = (
    '"Segoe Script", "Brush Script MT", "Snell Roundhand", "Apple Chancery", cursive'
)

# ReportLab built-in font for PDF signature rendering.
SIGNATURE_PDF_FONT = "Helvetica-Oblique"

SIGNATURE_METHOD_DRAWN_LEGACY = "drawn_legacy"
SIGNATURE_METHOD_TYPED = "typed"

SYNTHETIC_PDF_BANNER = "SYNTHETIC DEMO RECORD — NOT A REAL CONSENT FORM"
TYPED_SIGNATURE_ATTESTATION = "Electronically signed using the typed name shown above."


def typed_signature_png_bytes(name: str, *, width: int = 640, height: int = 140) -> bytes:
    """Rasterize typed signature text to PNG bytes for legacy PDF field placement."""
    from PIL import Image

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required to render typed signatures") from exc

    cleaned = " ".join(name.split())
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    font_size = 42.0
    while font_size > 14 and stringWidth(cleaned, SIGNATURE_PDF_FONT, font_size) > width - 48:
        font_size -= 1.5
    pdf.setFont(SIGNATURE_PDF_FONT, font_size)
    pdf.drawString(24, height / 2 - font_size / 3, cleaned)
    pdf.save()
    buffer.seek(0)
    doc = fitz.open(stream=buffer.read(), filetype="pdf")
    try:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        out = io.BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()
    finally:
        doc.close()
