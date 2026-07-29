"""One-time import: 50k fictional participant/parent name pairs from source PDF."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source" / "50000_fictional_names_with_parents.pdf"
OUTPUT = ROOT / "app" / "data" / "fictional_name_pairs.json"
EXPECTED = 50_000

PARTICIPANT_LINE = re.compile(r"^([\d,]+)\.\s+(.+)$")
PARENT_LINE = re.compile(r"^Parent:\s*(.+)$", re.IGNORECASE)


def extract_pairs() -> list[dict[str, str | int]]:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Source PDF missing: {SOURCE}")
    reader = PdfReader(str(SOURCE))
    pairs: list[dict[str, str | int]] = []
    seen_indices: set[int] = set()
    pending_index: int | None = None
    pending_participant: str | None = None

    for page in reader.pages:
        for raw_line in (page.extract_text() or "").splitlines():
            line = " ".join(raw_line.split())
            if not line or line.startswith("Page ") or "Fictional" in line and "sample" in line:
                continue
            participant_match = PARTICIPANT_LINE.match(line)
            if participant_match:
                pending_index = int(participant_match.group(1).replace(",", ""))
                pending_participant = participant_match.group(2).strip()
                continue
            parent_match = PARENT_LINE.match(line)
            if parent_match and pending_index is not None and pending_participant:
                parent_name = parent_match.group(1).strip()
                participant_name = pending_participant
                if pending_index not in seen_indices and participant_name and parent_name:
                    seen_indices.add(pending_index)
                    pairs.append(
                        {
                            "source_index": pending_index,
                            "participant_name": participant_name,
                            "parent_name": parent_name,
                        }
                    )
                pending_index = None
                pending_participant = None

    pairs.sort(key=lambda row: int(row["source_index"]))
    return pairs


def validate(pairs: list[dict[str, str | int]]) -> None:
    if len(pairs) < EXPECTED * 0.98:
        raise ValueError(f"Expected ~{EXPECTED} pairs, extracted {len(pairs)}")
    indices = [int(row["source_index"]) for row in pairs]
    if len(set(indices)) != len(indices):
        raise ValueError("Duplicate source_index values detected")
    dup_pairs = [
        pair
        for pair, count in Counter((p["participant_name"], p["parent_name"]) for p in pairs).items()
        if count > 1
    ]
    if dup_pairs:
        print(f"Warning: {len(dup_pairs)} duplicate exact pairs (allowed in source)", file=sys.stderr)
    missing = [i for i in range(1, max(indices) + 1) if i not in set(indices)]
    if len(missing) > 50:
        raise ValueError(f"Too many missing indices ({len(missing)}); first gaps: {missing[:10]}")


def main() -> int:
    pairs = extract_pairs()
    validate(pairs)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(pairs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"ok": True, "count": len(pairs), "output": str(OUTPUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
