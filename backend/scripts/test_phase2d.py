"""Phase 2D integration verification."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

BASE = "http://localhost:8000"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def split_participants(participant_ids, seed=42):
    import random

    unique_ids = list(dict.fromkeys(participant_ids))
    participant_count = len(unique_ids)
    if participant_count < 3:
        raise ValueError(f"Need at least 3 participants, found {participant_count}")

    rng = random.Random(seed)
    shuffled = unique_ids.copy()
    rng.shuffle(shuffled)

    train_count = max(1, int(round(participant_count * 0.70)))
    val_count = max(1, int(round(participant_count * 0.15)))
    test_count = participant_count - train_count - val_count

    while test_count < 1 and val_count > 1:
        val_count -= 1
        test_count = participant_count - train_count - val_count
    while test_count < 1 and train_count > 1:
        train_count -= 1
        test_count = participant_count - train_count - val_count

    train_ids = set(shuffled[:train_count])
    val_ids = set(shuffled[train_count : train_count + val_count])
    test_ids = set(shuffled[train_count + val_count :])
    return train_ids, val_ids, test_ids


def req(method, path, body=None, token=None, expect_error=False):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        err = exc.read().decode()
        if expect_error:
            try:
                return exc.code, json.loads(err) if err else None
            except json.JSONDecodeError:
                return exc.code, err
        raise


def _module_payloads(*, burnout_day: bool = False) -> dict[str, dict]:
    survey = {
        "stress": 9 if burnout_day else 4,
        "fatigue": 9 if burnout_day else 4,
        "motivation": 2 if burnout_day else 6,
        "mood": 5,
        "sleep": 7,
        "study": 2,
        "homework": 1,
        "exam": False,
        "socialStress": 3,
        "physicalActivity": 4,
    }
    return {
        "reaction": {"avg": 300, "median": 290, "sd": 40, "min": 200, "max": 400, "missed": 1, "trials": 20},
        "typing": {"wpm": 45, "errorRate": 0.05, "backspaces": 2, "avgInterval": 120, "variance": 15, "avgDwell": 80, "burstLength": 5, "pauseFrequency": 0.2, "totalKeys": 120, "errCorrectionRate": 0.1},
        "memory": {"accuracy": 80, "responseTime": 1500, "distractionScore": 0.2},
        "attention": {"accuracy": 85, "avgRT": 600, "errors": 2, "congruentAcc": 90, "incongruentAcc": 75},
        "survey": survey,
        "nasaTLX": {"mentalDemand": 60, "physicalDemand": 20, "temporalDemand": 50, "performance": 70, "effort": 65, "frustration": 40, "tlxScore": 50},
    }


def seed_training_cohort() -> None:
    from app.database import SessionLocal
    from app.models.daily_session import DailySession
    from app.models.module_result import ModuleResult
    from app.models.participant import Participant
    from app.utils.security import hash_pin

    db = SessionLocal()
    try:
        base_date = date.today() - timedelta(days=5)
        for index in range(3):
            participant = Participant(
                public_id=f"MLSEED{index}{uuid4().hex[:6].upper()}",
                pin_hash=hash_pin("1234"),
                grade="10th Grade",
                age_range="15-16",
                pet_choice="fox",
            )
            db.add(participant)
            db.flush()
            for offset in range(2):
                session_date = base_date + timedelta(days=offset + index)
                session = DailySession(
                    participant_id=participant.id,
                    session_date=session_date,
                    complete=True,
                )
                db.add(session)
                db.flush()
                payloads = _module_payloads(burnout_day=offset == 1)
                for module_key, payload in payloads.items():
                    db.add(
                        ModuleResult(
                            session_id=session.id,
                            module_key=module_key,
                            payload=payload,
                        )
                    )
        db.commit()
    finally:
        db.close()


def test_split_no_overlap():
    ids = [uuid4() for _ in range(6)]
    train_ids, val_ids, test_ids = split_participants(ids)
    assert not (train_ids & val_ids)
    assert not (train_ids & test_ids)
    assert not (val_ids & test_ids)
    assert len(train_ids) + len(val_ids) + len(test_ids) == 6
    print("split_participants: no overlap OK")


def main():
    test_split_no_overlap()

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
    token = login["access_token"]

    seed_training_cohort()
    _, ds = req("POST", "/v1/research/datasets/build", {"name": "phase-2d-training-set"}, token=token)
    dataset_id = ds["id"]
    print("build", ds["row_count"], "rows")

    req("POST", f"/v1/research/datasets/{dataset_id}/label", token=token)
    _, labels = req("GET", f"/v1/research/datasets/{dataset_id}/labels", token=token)
    print("valid_training_rows", labels["valid_training_rows"])

    status, train_resp = req(
        "POST",
        "/v1/research/models/train",
        {
            "dataset_id": dataset_id,
            "target_label": "burnout_next_day",
            "model_type": "lightgbm",
        },
        token=token,
        expect_error=True,
    )
    assert status == 201, train_resp
    model_id = train_resp["model_id"]
    print("train", status, "model_id", model_id)
    assert train_resp["status"] == "completed"
    assert train_resp["metrics"]["participant_counts"]["train"] >= 1
    assert train_resp["metrics"]["participant_counts"]["test"] >= 1

    _, model = req("GET", f"/v1/research/models/{model_id}", token=token)
    assert model["feature_importance"]["features"]
    assert model["metrics"]["test"]["f1_score"] is not None
    print("metrics and feature importance saved OK")

    artifact = ROOT / model["artifact_path"]
    assert artifact.exists(), f"missing artifact {artifact}"
    print("model artifact saved OK")

    _, models = req("GET", "/v1/research/models", token=token)
    assert any(item["id"] == model_id for item in models)
    print("models list OK")

    preg = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                BASE + "/v1/auth/participant/register",
                data=json.dumps(
                    {
                        "grade": "9th Grade",
                        "age_range": "13-14",
                        "pet_choice": "fox",
                        "pin": "9292",
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ).read().decode()
    )
    for path, method in [
        ("/v1/research/models/train", "POST"),
        ("/v1/research/models", "GET"),
    ]:
        code, _ = req(
            method,
            path,
            {"dataset_id": dataset_id, "target_label": "burnout_next_day", "model_type": "lightgbm"}
            if method == "POST"
            else None,
            token=preg["access_token"],
            expect_error=True,
        )
        assert code == 403, path
    print("participant blocked OK")
    print("ALL PHASE 2D TESTS PASSED")


if __name__ == "__main__":
    main()
