"""Shared typed-signature typography for browser UI and PDF generation."""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

SIGNATURE_FONT_FILE_NAME = "DancingScript-Regular.ttf"
SIGNATURE_PDF_FONT_NAME = "DancingScript"
SIGNATURE_FONT_FAMILY_CSS = '"Dancing Script", cursive'

SIGNATURE_METHOD_DRAWN_LEGACY = "drawn_legacy"
SIGNATURE_METHOD_TYPED = "typed"

SYNTHETIC_PDF_BANNER = "SYNTHETIC DEMO RECORD — NOT A REAL CONSENT FORM"
TYPED_SIGNATURE_ATTESTATION = "Electronically signed using the typed name shown above."

DISALLOWED_SIGNATURE_PDF_FONTS = frozenset({"Helvetica-Oblique", "HelveticaOblique"})


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def signature_font_path() -> Path:
    path = repo_root() / "src" / "assets" / "fonts" / SIGNATURE_FONT_FILE_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"Signature font not found at {path}. "
            "Run backend/scripts/install_signature_font.py or place DancingScript-Regular.ttf there."
        )
    return path


@lru_cache(maxsize=1)
def register_signature_pdf_font() -> str:
    font_path = signature_font_path()
    if SIGNATURE_PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(SIGNATURE_PDF_FONT_NAME, str(font_path)))
    return SIGNATURE_PDF_FONT_NAME


def signature_font_size_for_width(name: str, max_width: float, *, max_size: float = 42.0, min_size: float = 12.0) -> float:
    font_name = register_signature_pdf_font()
    cleaned = " ".join(name.split())
    size = max_size
    while size > min_size and pdfmetrics.stringWidth(cleaned, font_name, size) > max_width:
        size -= 0.5
    return size


def draw_typed_signature_on_canvas(
    pdf_canvas: canvas.Canvas,
    rect: list[float],
    name: str,
) -> None:
    """Draw cursive signature text inside an AcroForm signature rectangle (PDF bottom-left coords)."""
    font_name = register_signature_pdf_font()
    cleaned = " ".join(name.split())
    x0, y0, x1, y1 = rect
    width = max(1.0, x1 - x0 - 4.0)
    height = max(1.0, y1 - y0)
    font_size = min(signature_font_size_for_width(cleaned, width, max_size=min(36.0, height * 0.85)), height * 0.75)
    pdf_canvas.setFont(font_name, font_size)
    text_width = pdfmetrics.stringWidth(cleaned, font_name, font_size)
    x = x0 + max(2.0, (x1 - x0 - text_width) / 2)
    baseline = y0 + max(2.0, (height - font_size) * 0.45)
    pdf_canvas.drawString(x, baseline, cleaned)


def typed_signature_png_bytes(name: str, *, width: int = 640, height: int = 140) -> bytes:
    """High-resolution raster preview using the same embedded TTF as PDF generation."""
    from PIL import Image

    font_name = register_signature_pdf_font()
    cleaned = " ".join(name.split())
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    draw_typed_signature_on_canvas(pdf, [0, 0, width, height], cleaned)
    pdf.save()
    buffer.seek(0)

    try:
        import fitz  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required to rasterize typed signatures for legacy field placement") from exc

    doc = fitz.open(stream=buffer.read(), filetype="pdf")
    try:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        out = io.BytesIO()
        image.save(out, format="PNG")
        return out.getvalue()
    finally:
        doc.close()


def pdf_embeds_signature_font(pdf_bytes: bytes) -> bool:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf_bytes))
    page = reader.pages[0]
    fonts = page.get("/Resources", {}).get("/Font", {}) or {}
    for font_ref in fonts.values():
        obj = font_ref.get_object() if hasattr(font_ref, "get_object") else font_ref
        base = str(obj.get("/BaseFont", ""))
        if SIGNATURE_PDF_FONT_NAME in base or "DancingScript" in base:
            return True
    return False
