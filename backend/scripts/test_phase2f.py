"""Phase 2F integration verification."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://localhost:8000"


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


def seed_training_cohort():
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
                public_id=f"MLSHAP{index}{uuid4().hex[:6].upper()}",
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
                survey = {
                    "stress": 9 if offset == 1 else 4,
                    "fatigue": 9 if offset == 1 else 4,
                    "motivation": 2 if offset == 1 else 6,
                    "mood": 5,
                    "sleep": 5 if offset == 1 else 7,
                    "study": 2,
                    "homework": 1,
                    "exam": False,
                    "socialStress": 3,
                    "physicalActivity": 4,
                }
                payloads = {
                    "reaction": {"avg": 320, "median": 310, "sd": 45, "min": 210, "max": 420, "missed": 1, "trials": 20},
                    "typing": {"wpm": 45, "errorRate": 0.05, "backspaces": 2, "avgInterval": 120, "variance": 15, "avgDwell": 80, "burstLength": 5, "pauseFrequency": 0.2, "totalKeys": 120, "errCorrectionRate": 0.1},
                    "memory": {"accuracy": 80, "responseTime": 1500, "distractionScore": 0.2},
                    "attention": {"accuracy": 85, "avgRT": 600, "errors": 2, "congruentAcc": 90, "incongruentAcc": 75},
                    "survey": survey,
                    "nasaTLX": {"mentalDemand": 60, "physicalDemand": 20, "temporalDemand": 50, "performance": 70, "effort": 65, "frustration": 40, "tlxScore": 50},
                }
                for module_key, payload in payloads.items():
                    db.add(ModuleResult(session_id=session.id, module_key=module_key, payload=payload))
        db.commit()
    finally:
        db.close()


def main():
    from sqlalchemy import select, text
    from app.database import SessionLocal
    from app.models.daily_session import DailySession
    from app.models.participant import Participant

    token = researcher_token()
    seed_training_cohort()

    _, ds = req("POST", "/v1/research/datasets/build", {"name": "phase-2f-set"}, token=token)
    req("POST", f"/v1/research/datasets/{ds['id']}/label", token=token)
    _, train_resp = req(
        "POST",
        "/v1/research/models/train",
        {"dataset_id": ds["id"], "target_label": "burnout_next_day", "model_type": "lightgbm"},
        token=token,
    )
    model_id = train_resp["model_id"]

    db = SessionLocal()
    participant = db.execute(
        select(Participant).where(Participant.public_id.like("MLSHAP%")).order_by(Participant.created_at.desc())
    ).scalars().first()
    session = db.execute(
        select(DailySession)
        .where(DailySession.participant_id == participant.id)
        .order_by(DailySession.session_date.asc())
    ).scalars().first()
    db.close()

    _, predict_resp = req(
        "POST",
        f"/v1/research/models/{model_id}/predict",
        {"participant_id": str(participant.id), "session_date": session.session_date.isoformat()},
        token=token,
    )
    prediction_id = predict_resp["prediction_id"]

    status, explain_resp = req("POST", f"/v1/research/predictions/{prediction_id}/explain", token=token)
    assert status == 201, explain_resp
    explanation = explain_resp["explanation"]
    assert "contributions" in explanation
    assert len(explanation["contributions"]) <= 10
    assert 0.0 <= explanation["prediction_probability"] <= 1.0
    assert "burnout_next_day" not in json.dumps(explanation)
    print("SHAP explain OK", len(explanation["contributions"]), "contributions")

    _, get_resp = req("GET", f"/v1/research/predictions/{prediction_id}/explanation", token=token)
    assert get_resp["explanation"]["contributions"]
    print("GET explanation OK")

    _, importance = req("GET", f"/v1/research/models/{model_id}/feature-importance", token=token)
    assert importance["training_feature_importance"]
    assert importance["ranked_features"]
    print("feature importance OK")

    _, comparison = req("GET", "/v1/research/models/compare", token=token)
    assert len(comparison) >= 1
    assert "roc_auc" in comparison[0]
    print("model comparison OK", len(comparison))

    db = SessionLocal()
    count = db.execute(text("select count(*) from ml_explanations")).scalar_one()
    db.close()
    assert count >= 1
    print("explanation saved OK", count)

    preg = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                BASE + "/v1/auth/participant/register",
                data=json.dumps({"grade": "9th Grade", "age_range": "13-14", "pet_choice": "fox", "pin": "9494"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        ).read().decode()
    )
    for path, method in [
        (f"/v1/research/predictions/{prediction_id}/explain", "POST"),
        (f"/v1/research/predictions/{prediction_id}/explanation", "GET"),
        (f"/v1/research/models/{model_id}/feature-importance", "GET"),
        ("/v1/research/models/compare", "GET"),
    ]:
        code, _ = req(method, path, token=preg["access_token"], expect_error=True)
        assert code == 403, path
    print("participant blocked OK")
    print("ALL PHASE 2F TESTS PASSED")


if __name__ == "__main__":
    main()
