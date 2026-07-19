"""Create a development-only placeholder for 4-Human-Participants.pdf.

The official ISEF template must be copied manually to backend/templates/.
This script will never overwrite an existing official template.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "4-Human-Participants.pdf"
OFFICIAL_SHA256 = "e53b2ef301b1cf665e3ea4f3a18b970b3fcd0f0d15baf926379e94b33337baeb"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_template(*, force: bool = False) -> Path:
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    if TEMPLATE.exists():
        if _sha256(TEMPLATE).lower() == OFFICIAL_SHA256.lower():
            raise RuntimeError(
                "Refusing to overwrite the official ISEF Form 4 template at "
                f"{TEMPLATE}. Use ALLOW_FORM4_PLACEHOLDER only when no official file exists."
            )
        if not force:
            raise RuntimeError(
                f"Template already exists at {TEMPLATE}. Pass force=True only for explicit dev placeholder creation."
            )
    pdf = canvas.Canvas(str(TEMPLATE), pagesize=letter)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(36, 760, "DEV PLACEHOLDER - NOT FOR PILOT/PRODUCTION")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(36, 730, "Replace with official 4-Human-Participants.pdf before pilot use.")
    pdf.save()
    return TEMPLATE


if __name__ == "__main__":
    force = "--force" in sys.argv
    try:
        path = create_template(force=force)
        print("Created development placeholder:", path)
    except RuntimeError as exc:
        print(str(exc))
        sys.exit(1)
