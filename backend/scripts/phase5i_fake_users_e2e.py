#!/usr/bin/env python3
"""Phase 5I fake-user E2E via TestClient (no live server required)."""
from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.utils.security import create_golden_vault_access_token, hash_invite_code


def main() -> int:
    import os
    from pathlib import Path

    code_path = Path(__file__).resolve().parents[1] / ".golden_vault_local"
    code = os.environ.get("GOLDEN_VAULT_TEST_CODE")
    if not code and code_path.is_file():
        code = code_path.read_text(encoding="utf-8").strip()
    if not code:
        code = f"phase5i-{uuid.uuid4()}"
    os.environ["GOLDEN_VAULT_ENABLED"] = "true"
    os.environ["GOLDEN_VAULT_CODE_HASH"] = hash_invite_code(code)
    get_settings.cache_clear()

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_golden_vault_access_token()}"}
    report: dict = {"ok": False, "timings": {}, "checks": []}

    warm_start = time.perf_counter()
    client.get("/v1/golden-vault/participants?limit=50&offset=0", headers=headers)
    report["timings"]["warmGoldenVaultListMs"] = round((time.perf_counter() - warm_start) * 1000)

    body = {
        "total": 10,
        "start_date": "2026-01-10",
        "daily": 3,
        "weekly": 2,
        "two_days": 3,
        "four_days": 2,
    }
    preview_start = time.perf_counter()
    preview = client.post("/v1/golden-vault/fake-users/preview", json=body, headers=headers)
    report["timings"]["fakeUserPreviewMs"] = round((time.perf_counter() - preview_start) * 1000)
    report["checks"].append({"name": "preview_ok", "ok": preview.status_code == 200})

    gen_start = time.perf_counter()
    created = client.post(
        "/v1/golden-vault/fake-users/generate",
        json={**body, "idempotency_key": str(uuid.uuid4())},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    batch_id = created.json()["batchId"]
    status = created.json()["status"]
    while status not in {"completed", "completed_with_errors", "failed"}:
        step = client.post(f"/v1/golden-vault/fake-users/batches/{batch_id}/process", headers=headers)
        assert step.status_code == 200, step.text
        status = step.json()["status"]
    report["timings"]["tenUserGenerationMs"] = round((time.perf_counter() - gen_start) * 1000)

    batch = client.get(f"/v1/golden-vault/fake-users/batches/{batch_id}", headers=headers).json()
    report["checks"].append(
        {
            "name": "ten_users_created",
            "ok": batch["successfulCount"] == 10 and batch["processedCount"] == 10,
            "detail": batch,
        }
    )

    cred1 = client.get(f"/v1/golden-vault/fake-users/batches/{batch_id}/credentials", headers=headers)
    cred2 = client.get(f"/v1/golden-vault/fake-users/batches/{batch_id}/credentials", headers=headers)
    credentials = cred1.json().get("credentials", [])
    public_ids = [c["publicId"] for c in credentials]
    report["checks"].append({"name": "credentials_once", "ok": cred1.status_code == 200 and len(credentials) == 10})
    report["checks"].append({"name": "credentials_410_second", "ok": cred2.status_code == 410})
    report["checks"].append({"name": "unique_public_ids", "ok": len(set(public_ids)) == 10})

    listed = client.get(
        f"/v1/golden-vault/participants?synthetic_batch_id={batch_id}&limit=50",
        headers=headers,
    )
    report["checks"].append({"name": "vault_batch_filter", "ok": listed.json().get("total") == 10})

    from subprocess import run

    verify = run(
        [sys.executable, str(BACKEND / "scripts" / "verify_fake_user_batch.py"), batch_id, ",".join(public_ids)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )
    db_verify = json.loads(verify.stdout.strip() or "{}")
    report["checks"].append({"name": "db_verify", "ok": verify.returncode == 0, "detail": db_verify})

    report["ok"] = all(c["ok"] for c in report["checks"])
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
