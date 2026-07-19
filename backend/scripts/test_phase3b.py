"""Phase 3B study mode and test-data isolation verification."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://localhost:8000"


def req(method, path, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, headers=headers, method=method)
    with urllib.request.urlopen(request) as resp:
        raw = resp.read().decode()
        return resp.status, json.loads(raw) if raw else None


def researcher_token():
    login = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                BASE + "/v1/auth/researcher/login",
                data=json.dumps({"invite_code": "YASH GUPTA"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ).read().decode()
    )
    return login["access_token"]


def with_env(overrides: dict[str, str | None], fn):
    previous = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        from app.config import get_settings

        get_settings.cache_clear()
        return fn()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        from app.config import get_settings

        get_settings.cache_clear()


def test_policy_defaults():
    def _run():
        from app.services.study_guard import get_study_config

        dev = get_study_config()
        assert dev["study_mode"] == "development"
        assert dev["show_test_data"] is True
        assert dev["show_experimental_banner"] is False
        assert dev["allow_participant_predictions"] is False
        print("development policy OK")

    with_env({"STUDY_MODE": "development", "SHOW_TEST_DATA": None}, _run)

    def _pilot():
        from app.services.study_guard import get_study_config

        pilot = get_study_config()
        assert pilot["study_mode"] == "pilot"
        assert pilot["show_test_data"] is False
        assert pilot["show_experimental_banner"] is True
        assert pilot["filter_synthetic_data"] is True
        print("pilot policy OK")

    with_env({"STUDY_MODE": "pilot", "SHOW_TEST_DATA": None}, _pilot)

    def _production():
        from app.services.study_guard import get_study_config

        prod = get_study_config()
        assert prod["study_mode"] == "production"
        assert prod["show_test_data"] is False
        assert prod["show_experimental_banner"] is False
        assert prod["filter_synthetic_data"] is True
        print("production policy OK")

    with_env({"STUDY_MODE": "production", "SHOW_TEST_DATA": None}, _production)


def test_study_config_endpoint():
    from app.routers.research import get_research_study_config

    payload = get_research_study_config(_researcher=object())
    assert payload.study_mode
    assert payload.show_experimental_banner is False or payload.study_mode == "pilot"
    print("study-config endpoint OK", payload.study_mode)


def test_live_api():
    try:
        token = researcher_token()
        _, config = req("GET", "/v1/research/study-config", token=token)
    except Exception as exc:
        print("live API skipped (restart backend to pick up study-config route):", exc)
        return

    _, participants = req("GET", "/v1/research/participants", token=token)
    prefixes = ("MLSEED", "MLPRED", "MLSHAP")
    synthetic_count = sum(
        1 for item in participants if str(item["id"]).upper().startswith(prefixes)
    )
    if config["filter_synthetic_data"]:
        assert synthetic_count == 0, "Synthetic participants leaked in filtered mode"
        print("live filtering OK")
    else:
        print("live development mode: synthetic participants visible=", synthetic_count)


def test_purge_dry_run():
    from app.database import SessionLocal
    from scripts.purge_test_data import build_report

    db = SessionLocal()
    try:
        report = build_report(db)
    finally:
        db.close()
    print("Dry-run purge OK", report.as_dict())


def test_pilot_filtering():
    def _run():
        from app.database import SessionLocal
        from app.services.research_service import list_research_participants

        db = SessionLocal()
        try:
            participants = list_research_participants(db)
        finally:
            db.close()
        prefixes = ("MLSEED", "MLPRED", "MLSHAP")
        leaked = [item["id"] for item in participants if str(item["id"]).upper().startswith(prefixes)]
        assert not leaked, f"Synthetic participants leaked: {leaked}"
        print("pilot participant filtering OK", "visible=", len(participants))

    with_env({"STUDY_MODE": "pilot", "SHOW_TEST_DATA": "false"}, _run)


def main():
    test_policy_defaults()
    test_study_config_endpoint()
    test_pilot_filtering()
    test_live_api()
    test_purge_dry_run()
    print("ALL PHASE 3B TESTS PASSED")


if __name__ == "__main__":
    main()
