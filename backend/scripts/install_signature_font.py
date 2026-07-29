"""Install Dancing Script Regular and its complete license for consent signatures."""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST_DIR = ROOT / "src" / "assets" / "fonts"
DEST_FILE = DEST_DIR / "DancingScript-Regular.ttf"
OFL_FILE = DEST_DIR / "OFL.txt"

FONT_DOWNLOAD_URL = (
    "https://cdn.jsdelivr.net/fontsource/fonts/"
    "dancing-script@5.2.5/latin-400-normal.ttf"
)
LICENSE_DOWNLOAD_URL = (
    "https://raw.githubusercontent.com/google/fonts/"
    "main/ofl/dancingscript/OFL.txt"
)


def download_file(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=30) as response:
        destination.write_bytes(response.read())


def main() -> int:
    DEST_DIR.mkdir(parents=True, exist_ok=True)

    if not DEST_FILE.is_file() or DEST_FILE.stat().st_size < 10_000:
        print(f"Downloading font from {FONT_DOWNLOAD_URL} ...")
        download_file(FONT_DOWNLOAD_URL, DEST_FILE)
    else:
        print(
            f"Font already present: {DEST_FILE} "
            f"({DEST_FILE.stat().st_size} bytes)"
        )

    if not OFL_FILE.is_file() or OFL_FILE.stat().st_size < 4_000:
        print(f"Downloading license from {LICENSE_DOWNLOAD_URL} ...")
        download_file(LICENSE_DOWNLOAD_URL, OFL_FILE)
    else:
        print(
            f"License already present: {OFL_FILE} "
            f"({OFL_FILE.stat().st_size} bytes)"
        )

    font_size = DEST_FILE.stat().st_size
    license_size = OFL_FILE.stat().st_size

    if font_size < 10_000:
        print("Downloaded font file looks too small.", file=sys.stderr)
        return 1

    if license_size < 4_000:
        print("Downloaded license file looks incomplete.", file=sys.stderr)
        return 1

    print(f"Installed font ({font_size} bytes)")
    print(f"Installed license ({license_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
