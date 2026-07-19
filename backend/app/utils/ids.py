import secrets
import string
import time


def generate_public_id() -> str:
    """Match frontend NC- ID format: NC-<timestamp36><random4>."""
    ts = int(time.time() * 1000)
    ts_part = _base36(ts).upper()
    rand_part = "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)
    )
    return f"NC-{ts_part}{rand_part}"


def _base36(number: int) -> str:
    if number == 0:
        return "0"
    alphabet = string.digits + string.ascii_lowercase
    chars: list[str] = []
    n = number
    while n:
        n, remainder = divmod(n, 36)
        chars.append(alphabet[remainder])
    return "".join(reversed(chars))
