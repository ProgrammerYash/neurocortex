"""Process due Golden Vault automatic bonus sessions (safe stdout summary only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.services.golden_vault_auto_session_service import process_due_golden_auto_sessions


def main() -> int:
    try:
        with SessionLocal() as db:
            summary = process_due_golden_auto_sessions(db)
            db.commit()
        print(json.dumps({"ok": True, **summary}))
        return 0 if summary.get("errors", 0) == 0 else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
