from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_PET_TYPES = frozenset({"fox", "owl", "cat", "dragon"})


class GameDataPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    pet: dict[str, Any]
    coins: int = Field(default=0, ge=0)
    streak: int = Field(default=0, ge=0)
    longestStreak: int = Field(default=0, ge=0)
    totalDays: int = Field(default=0, ge=0)
    lastCompleted: str | None = None
    house: dict[str, Any]
    achievements: list[str] = Field(default_factory=list)
    unlockedRegions: list[str] = Field(default_factory=list)
    milestones: list[Any] = Field(default_factory=list)

    @field_validator("pet")
    @classmethod
    def validate_pet(cls, value: dict[str, Any]) -> dict[str, Any]:
        pet_type = value.get("type")
        if pet_type not in VALID_PET_TYPES:
            raise ValueError(f"pet.type must be one of: {', '.join(sorted(VALID_PET_TYPES))}")
        return value

    @field_validator("house")
    @classmethod
    def validate_house(cls, value: dict[str, Any]) -> dict[str, Any]:
        items = value.get("items")
        if items is not None and not isinstance(items, list):
            raise ValueError("house.items must be a list")
        return value
