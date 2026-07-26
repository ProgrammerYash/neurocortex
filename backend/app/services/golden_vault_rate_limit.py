"""In-memory rate limiting for Golden Vault login attempts."""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_LOCK = threading.Lock()
_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_WINDOW_SECONDS = 900
_MAX_ATTEMPTS = 8


def check_golden_vault_login_allowed(client_key: str) -> bool:
    now = time.monotonic()
    with _LOCK:
        bucket = _ATTEMPTS[client_key]
        cutoff = now - _WINDOW_SECONDS
        _ATTEMPTS[client_key] = [t for t in bucket if t >= cutoff]
        if len(_ATTEMPTS[client_key]) >= _MAX_ATTEMPTS:
            return False
        return True


def record_golden_vault_login_failure(client_key: str) -> None:
    now = time.monotonic()
    with _LOCK:
        _ATTEMPTS[client_key].append(now)


def reset_golden_vault_login_attempts(client_key: str) -> None:
    with _LOCK:
        _ATTEMPTS.pop(client_key, None)
