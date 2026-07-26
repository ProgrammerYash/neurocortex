"""Create a one-time researcher invite for browser QA (prints JSON only)."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.database import SessionLocal
from app.models.researcher import Researcher
from app.models.researcher_invite import ResearcherInvite
from app.utils.security import hash_invite_code


def main() -> None:
    code = f"browser-r-{uuid.uuid4().hex[:10]}"
    with SessionLocal() as db:
        researcher = Researcher(
            display_name="Browser QA Researcher",
            email=f"browser-qa-{uuid.uuid4().hex}@example.test",
        )
        db.add(researcher)
        db.flush()
        db.add(
            ResearcherInvite(
                researcher_id=researcher.id,
                code_hash=hash_invite_code(code),
            )
        )
        db.commit()
    print(json.dumps({"researcherCode": code}))


if __name__ == "__main__":
    main()
