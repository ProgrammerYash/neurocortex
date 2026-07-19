from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


VALID_MODULE_KEYS = frozenset({"reaction", "typing", "memory", "attention", "survey", "nasaTLX"})
CORE_MODULE_KEYS = frozenset({"reaction", "typing", "memory", "attention", "survey"})


class ModuleUpsertRequest(BaseModel):
    payload: dict[str, Any]


class DailySessionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    date: str
    sessionId: str
    complete: bool
    status: str | None = None
    sessionSlot: int | None = None
