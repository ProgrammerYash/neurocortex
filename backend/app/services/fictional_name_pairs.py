"""Runtime access to imported fictional participant/parent name pairs."""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "fictional_name_pairs.json"


class FictionalNamePairsError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_name_pairs() -> tuple[dict[str, Any], ...]:
    if not DATA_PATH.is_file():
        raise FictionalNamePairsError(
            f"Name pair dataset missing at {DATA_PATH}. Run backend/scripts/import_fictional_name_pairs.py."
        )
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise FictionalNamePairsError("Name pair dataset is empty or invalid")
    return tuple(raw)


def pair_count() -> int:
    return len(load_name_pairs())


def select_pairs_deterministic(*, batch_key: str, count: int, start_offset: int = 0) -> list[dict[str, Any]]:
    """Deterministic selection for idempotent fake-user batches."""
    pairs = load_name_pairs()
    if count > len(pairs):
        raise FictionalNamePairsError("Requested count exceeds available name pairs")
    seed = hash((batch_key, start_offset)) & 0xFFFFFFFF
    rng = random.Random(seed)
    indices = list(range(len(pairs)))
    rng.shuffle(indices)
    chosen = indices[start_offset : start_offset + count]
    return [pairs[i] for i in chosen]
