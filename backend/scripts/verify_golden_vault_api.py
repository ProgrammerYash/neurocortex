"""Non-interactive Golden Vault verification for local QA (no secrets printed)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
CODE_PATH = BACKEND / ".golden_vault_local"
BASE = "http://127.0.0.1:8000"


def main() -> int:
    if not CODE_PATH.exists():
        print(json.dumps({"ok": False, "error": "missing .golden_vault_local"}))
        return 1
    code = CODE_PATH.read_text(encoding="utf-8").strip()
    wrong = "definitely-wrong-vault-code-000"
    out: dict[str, object] = {"checks": []}

    def check(name: str, ok: bool, detail: str = "") -> None:
        out["checks"].append({"name": name, "ok": ok, "detail": detail})

    def post(path: str, payload: dict) -> tuple[int, dict]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {}
            return exc.code, parsed

    def get(path: str, headers: dict | None = None) -> int:
        req = urllib.request.Request(f"{BASE}{path}", headers=headers or {}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code

    bad_status, _ = post("/v1/golden-vault/login", {"code": wrong})
    check("incorrect_code_rejected", bad_status in {401, 429}, f"status={bad_status}")

    good_status, good_body = post("/v1/golden-vault/login", {"code": code})
    check("golden_login_ok", good_status == 200, f"status={good_status}")
    if good_status != 200:
        print(json.dumps(out))
        return 1
    token = good_body["access_token"]
    g_headers = {"Authorization": f"Bearer {token}"}

    blocked = get("/v1/research/dashboard/summary", g_headers)
    check("golden_cannot_access_researcher_summary", blocked == 403, f"status={blocked}")

    listed = get("/v1/golden-vault/participants?limit=5", g_headers)
    check("golden_lists_participants", listed == 200, f"status={listed}")

    out["ok"] = all(item["ok"] for item in out["checks"])
    print(json.dumps(out, indent=2))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
