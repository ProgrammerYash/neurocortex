#!/usr/bin/env python3
"""Verify Phase 5I fake-user batch invariants (no Groq sessions, PDF banner, etc.)."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.consent_record import ConsentRecord  # noqa: E402
from app.models.daily_session import DailySession  # noqa: E402
from app.models.golden_demo_override import GoldenDemoOverride  # noqa: E402
from app.models.module_result import ModuleResult  # noqa: E402
from app.models.participant import Participant  # noqa: E402
from app.models.participant_feedback_snapshot import ParticipantFeedbackSnapshot  # noqa: E402
from app.services.consent_pdf_service import _pdf_contains_synthetic_marker  # noqa: E402
from app.services.study_frequency import (  # noqa: E402
    STUDY_FREQUENCY_DAILY,
    STUDY_FREQUENCY_FOUR_TIMES_WEEKLY,
    STUDY_FREQUENCY_TWICE_WEEKLY,
    STUDY_FREQUENCY_WEEKLY,
)


def main() -> int:
    if len(sys.argv) < 3:
        print(json.dumps({"ok": False, "error": "usage: verify_fake_user_batch.py <batch_id> <public_id,...>"}))
        return 1
    batch_id = uuid.UUID(sys.argv[1])
    public_ids = [p.strip() for p in sys.argv[2].split(",") if p.strip()]
    db = SessionLocal()
    try:
        participants = db.execute(
            select(Participant).where(Participant.public_id.in_(public_ids))
        ).scalars().all()
        overrides = db.execute(
            select(GoldenDemoOverride).where(GoldenDemoOverride.synthetic_batch_id == batch_id)
        ).scalars().all()
        freq_counts = {
            "daily": 0,
            "weekly": 0,
            "two_days": 0,
            "four_days": 0,
        }
        for row in overrides:
            sf = row.auto_data_frequency or STUDY_FREQUENCY_DAILY
            if sf == STUDY_FREQUENCY_DAILY:
                freq_counts["daily"] += 1
            elif sf == STUDY_FREQUENCY_WEEKLY:
                freq_counts["weekly"] += 1
            elif sf == STUDY_FREQUENCY_TWICE_WEEKLY:
                freq_counts["two_days"] += 1
            elif sf == STUDY_FREQUENCY_FOUR_TIMES_WEEKLY:
                freq_counts["four_days"] += 1
        pids = [p.id for p in participants]
        sessions = db.execute(
            select(func.count()).select_from(DailySession).where(DailySession.participant_id.in_(pids))
        ).scalar_one()
        modules = db.execute(
            select(func.count())
            .select_from(ModuleResult)
            .join(DailySession, DailySession.id == ModuleResult.session_id)
            .where(DailySession.participant_id.in_(pids))
        ).scalar_one()
        snapshots = db.execute(
            select(func.count())
            .select_from(ParticipantFeedbackSnapshot)
            .where(ParticipantFeedbackSnapshot.participant_id.in_(pids))
        ).scalar_one()
        consents = db.execute(
            select(ConsentRecord).where(ConsentRecord.participant_id.in_(pids))
        ).scalars().all()
        pdf_ok = all(_pdf_contains_synthetic_marker(c.pdf_bytes) for c in consents)
        typed_ok = all(c.signature_method == "typed" for c in consents)
        result = {
            "ok": (
                len(participants) == len(public_ids)
                and len(overrides) == len(public_ids)
                and freq_counts == {"daily": 3, "weekly": 2, "two_days": 3, "four_days": 2}
                and sessions == 0
                and modules == 0
                and snapshots == 0
                and pdf_ok
                and typed_ok
            ),
            "participantCount": len(participants),
            "overrideCount": len(overrides),
            "frequencyCounts": freq_counts,
            "dailySessions": sessions,
            "moduleResults": modules,
            "feedbackSnapshots": snapshots,
            "syntheticPdfBannerOk": pdf_ok,
            "typedSignaturesOk": typed_ok,
        }
        print(json.dumps(result))
        return 0 if result["ok"] else 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
