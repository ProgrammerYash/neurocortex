"""Configure local Golden Vault in backend/.env without printing secrets."""

from __future__ import annotations

import secrets
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.utils.security import hash_invite_code
ENV_PATH = BACKEND / ".env"
LOCAL_CODE_PATH = BACKEND / ".golden_vault_local"
MARKER = "# --- golden-vault-local (auto) ---"


def upsert_env_lines(lines: dict[str, str]) -> None:
    existing = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
    filtered = []
    skip = False
    for row in existing.splitlines():
        if row.strip() == MARKER:
            skip = True
            continue
        if skip:
            if row.startswith("# --- end golden-vault-local ---"):
                skip = False
            continue
        if any(row.startswith(f"{key}=") for key in lines):
            continue
        filtered.append(row)
    block = [MARKER, "# --- end golden-vault-local ---"]
    for key, value in lines.items():
        block.insert(-1, f"{key}={value}")
    merged = "\n".join([*filtered, *block, ""]).strip() + "\n"
    ENV_PATH.write_text(merged, encoding="utf-8")


def main() -> None:
    code = secrets.token_urlsafe(24)
    code_hash = hash_invite_code(code)
    upsert_env_lines(
        {
            "GOLDEN_VAULT_ENABLED": "true",
            "GOLDEN_OVERRIDES_VISIBLE": "true",
            "GOLDEN_VAULT_TOKEN_MINUTES": "30",
            "GOLDEN_VAULT_CODE_HASH": code_hash,
        }
    )
    LOCAL_CODE_PATH.write_text(code, encoding="utf-8")
    LOCAL_CODE_PATH.chmod(0o600)


if __name__ == "__main__":
    main()
