"""Verify synthetic Golden Vault users appear on researcher dashboard."""

from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.participant import Participant


def main() -> int:
    from app.database import SessionLocal

    client = TestClient(app)
    # Researcher login would be required for API — use service layer directly
    db = SessionLocal()
    try:
        synthetic_ids = {
            row.public_id
            for row in db.execute(
                select(Participant.public_id)
                .join(GoldenDemoOverride, GoldenDemoOverride.participant_id == Participant.id)
                .where(GoldenDemoOverride.is_synthetic_generated.is_(True))
            ).all()
        }
        from app.services.researcher_dashboard_service import list_dashboard_participants

        dashboard_items, total = list_dashboard_participants(
            db, limit=500, offset=0, search=None, sort="joined", direction="desc", participant_type_filter="all"
        )
        dashboard_ids = {row["participantId"] for row in dashboard_items}
        missing = sorted(synthetic_ids - dashboard_ids)
        payload = {
            "ok": len(missing) == 0,
            "syntheticInDb": len(synthetic_ids),
            "dashboardTotal": total,
            "missingFromDashboard": missing[:50],
            "missingCount": len(missing),
        }
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
