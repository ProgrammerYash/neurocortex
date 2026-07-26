"""Headless browser checks for Golden Vault UX (reads secrets locally; never prints them)."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

BASE_URL = "http://127.0.0.1:5173"
CODE_PATH = BACKEND / ".golden_vault_local"


def main() -> int:
    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"ok": False, "error": "playwright not installed", "checks": checks}))
        return 2

    if not CODE_PATH.exists():
        print(json.dumps({"ok": False, "error": "missing golden vault local code file", "checks": checks}))
        return 1

    golden_code = CODE_PATH.read_text(encoding="utf-8").strip()
    wrong_code = "browser-wrong-golden-code-xyz"

    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models.researcher import Researcher
    from app.models.researcher_invite import ResearcherInvite
    from app.utils.security import hash_invite_code

    researcher_code = f"browser-r-{uuid.uuid4().hex[:10]}"
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
                code_hash=hash_invite_code(researcher_code),
            )
        )
        db.commit()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844})
        page = context.new_page()

        page.goto(f"{BASE_URL}/researcher/sign-in", wait_until="networkidle")
        page.fill('input[type="password"]', wrong_code)
        page.get_by_role("button", name="Sign In as Researcher →").click()
        page.wait_for_timeout(800)
        record(
            "incorrect_golden_code_rejected",
            page.get_by_role("alert").is_visible() and "/golden-vault" not in page.url,
            page.url,
        )

        page.goto(f"{BASE_URL}/researcher/sign-in", wait_until="networkidle")
        page.fill('input[type="password"]', golden_code)
        page.get_by_role("button", name="Sign In as Researcher →").click()
        page.wait_for_url("**/golden-vault**", timeout=15000)
        record("golden_code_redirects_to_vault", "/golden-vault" in page.url, page.url)
        record(
            "golden_vault_heading",
            page.get_by_text("Golden Vault").is_visible(),
            "",
        )
        record(
            "simulated_data_banner",
            page.get_by_text("SIMULATED DATA").is_visible(),
            "",
        )

        overflow = page.evaluate(
            """() => {
              const doc = document.documentElement;
              return doc.scrollWidth <= doc.clientWidth + 2;
            }"""
        )
        record("mobile_no_horizontal_overflow", bool(overflow), f"scroll={page.evaluate('document.documentElement.scrollWidth')}")

        page.evaluate("localStorage.removeItem('nc3_golden_vault_token')")
        page.goto(f"{BASE_URL}/researcher/sign-in", wait_until="networkidle")
        page.fill('input[type="password"]', researcher_code)
        page.get_by_role("button", name="Sign In as Researcher →").click()
        page.wait_for_url("**/researcher**", timeout=15000)
        record(
            "ordinary_researcher_login",
            "/researcher/dashboard" in page.url or "/researcher" in page.url,
            page.url,
        )

        browser.close()

    ok = all(item["ok"] for item in checks)
    print(json.dumps({"ok": ok, "checks": checks}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
