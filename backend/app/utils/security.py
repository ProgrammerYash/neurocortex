from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


def hash_pin(pin: str) -> str:
    hashed = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def hash_invite_code(code: str) -> str:
    normalized = code.strip().lower().encode("utf-8")
    hashed = bcrypt.hashpw(normalized, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_pin(plain_pin: str, pin_hash: str) -> bool:
    return bcrypt.checkpw(plain_pin.encode("utf-8"), pin_hash.encode("utf-8"))


def verify_invite_code(plain_code: str, code_hash: str) -> bool:
    normalized = plain_code.strip().lower().encode("utf-8")
    return bcrypt.checkpw(normalized, code_hash.encode("utf-8"))


def create_access_token(*, participant_id: UUID, public_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(participant_id),
        "public_id": public_id,
        "role": "participant",
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_researcher_access_token(*, researcher_id: UUID, display_name: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(researcher_id),
        "display_name": display_name,
        "role": "researcher",
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )


def is_valid_token(token: str) -> bool:
    try:
        decode_access_token(token)
        return True
    except JWTError:
        return False
