"""End-to-end Golden Vault checks against running API (no stdout secrets)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.daily_session import DailySession
from app.models.golden_demo_override import GoldenDemoOverride
from app.models.module_result import ModuleResult
from app.models.participant import Participant
from app.models.participant_feedback_snapshot import ParticipantFeedbackSnapshot

BASE = "http://127.0.0.1:8000"
CODE_PATH = BACKEND / ".golden_vault_local"


def _request(method: str, path: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict | list | None]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return exc.code, parsed


def main() -> int:
    code = CODE_PATH.read_text(encoding="utf-8").strip()
    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    status, body = _request("POST", "/v1/golden-vault/login", body={"code": code})
    record("golden_login", status == 200, f"status={status}")
    if status != 200:
        print(json.dumps({"ok": False, "checks": checks}, indent=2))
        return 1
    token = body["access_token"]

    # pick first participant from vault list
    status, listed = _request("GET", "/v1/golden-vault/participants?limit=1", token=token)
    record("list_participants", status == 200 and listed.get("total", 0) >= 0, f"status={status}")
    if not listed.get("items"):
        print(json.dumps({"ok": False, "checks": checks, "error": "no participants"}, indent=2))
        return 1
    public_id = listed["items"][0]["participantId"]

    _request("PATCH", f"/v1/golden-vault/participants/{public_id}", token=token, body={"enabled": True})
    status, _ = _request("POST", f"/v1/golden-vault/participants/{public_id}/sessions", token=token, body={"set_to": 50})
    record("add_50_sessions", status == 200, f"status={status}")

    from app.models.researcher import Researcher
    from app.utils.security import create_researcher_access_token

    from uuid import uuid4

    with SessionLocal() as db:
        researcher_row = Researcher(
            display_name="GV Dash",
            email=f"gv-dash-{uuid4()}@example.test",
        )
        db.add(researcher_row)
        db.commit()
        r_token = create_researcher_access_token(
            researcher_id=researcher_row.id,
            display_name=researcher_row.display_name,
        )
    r_headers = {"Authorization": f"Bearer {r_token}"}
    status, detail = _request("GET", f"/v1/research/dashboard/participants/{public_id}", token=r_token)
    if status == 200 and isinstance(detail, dict):
        record(
            "researcher_dashboard_sessions_include_bonus",
            detail.get("sessionsCompleted", 0) >= 50 and detail.get("isDemoOverride") is True,
            f"sessionsCompleted={detail.get('sessionsCompleted')}",
        )
        record(
            "researcher_feedback_not_insufficient",
            detail.get("feedbackStatus") != "Insufficient Data",
            f"feedback={detail.get('feedbackStatus')}",
        )
        record(
            "researcher_display_status_active",
            detail.get("status") == "Active",
            f"status={detail.get('status')}",
        )
        last = detail.get("lastActiveDisplay") or ""
        record("researcher_last_active_present", ":" in last and "M" in last.upper(), last)
    else:
        record("researcher_dashboard_sessions_include_bonus", False, f"status={status}")

    with SessionLocal() as db:
        participant = db.execute(select(Participant).where(Participant.public_id == public_id)).scalar_one()
        ds = db.execute(select(func.count()).select_from(DailySession).where(DailySession.participant_id == participant.id)).scalar_one()
        mr = db.execute(select(func.count()).select_from(ModuleResult).join(DailySession).where(DailySession.participant_id == participant.id)).scalar_one()
        snaps = db.execute(
            select(func.count()).select_from(ParticipantFeedbackSnapshot).where(
                ParticipantFeedbackSnapshot.participant_id == participant.id
            )
        ).scalar_one()
        record("no_daily_sessions_created", ds == 0, f"count={ds}")
        record("no_module_results_created", mr == 0, f"count={mr}")
        record("no_feedback_snapshots", snaps == 0, f"count={snaps}")

        override = db.execute(
            select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
        ).scalar_one()
        first_reaction = override.simulated_reaction_ms
        record("last_active_minute_range", 14 * 60 <= (override.last_active_minute_of_day or 0) <= 20 * 60, "")

    status, row = _request("POST", f"/v1/golden-vault/participants/{public_id}/regenerate-metrics", token=token)
    record("regenerate_metrics", status == 200, f"status={status}")

    with SessionLocal() as db:
        participant = db.execute(select(Participant).where(Participant.public_id == public_id)).scalar_one()
        override = db.execute(
            select(GoldenDemoOverride).where(GoldenDemoOverride.participant_id == participant.id)
        ).scalar_one()
        record("metrics_persist_after_regenerate_call", override.simulated_reaction_ms is not None, "")
        record(
            "regenerate_changes_profile",
            override.simulated_reaction_ms != first_reaction or override.random_seed,
            "",
        )

    status, bulk = _request(
        "POST",
        "/v1/golden-vault/participants/bulk",
        token=token,
        body={"action": "add_sessions", "participant_public_ids": [public_id], "amount": 5},
    )
    record("bulk_add_sessions", status == 200 and bulk.get("succeeded_count") == 1, f"status={status}")

    status, bulk = _request(
        "POST",
        "/v1/golden-vault/participants/bulk",
        token=token,
        body={"action": "add_coins", "participant_public_ids": [public_id], "amount": 25},
    )
    record("bulk_add_coins", status == 200 and bulk.get("succeeded_count") == 1, f"status={status}")

    _request("PATCH", f"/v1/golden-vault/participants/{public_id}", token=token, body={"enabled": False})
    record("disable_override", True, "")

    ok = all(bool(c["ok"]) for c in checks)
    print(json.dumps({"ok": ok, "checks": checks, "sample_public_id": public_id}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
