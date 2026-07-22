from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

VALID_PET_CHOICES = frozenset({"fox", "owl", "cat", "dragon"})
VALID_AGE_CONSENT_CATEGORIES = frozenset({"under_18", "age_18_or_over"})


class ParticipantRegisterRequest(BaseModel):
    grade: str = Field(..., min_length=1, max_length=64)
    age_range: str = Field(..., min_length=1, max_length=32)
    age_consent_category: str | None = Field(default=None, pattern="^(under_18|age_18_or_over)$")
    pet_choice: str = Field(..., min_length=1, max_length=32)
    pin: str = Field(..., min_length=4, max_length=6)
    pin_confirmation: str = Field(..., min_length=4, max_length=6)
    participant_printed_name: str = Field(..., min_length=2, max_length=200)
    guardian_printed_name: str = Field(..., min_length=2, max_length=200)
    participant_acknowledged: bool
    guardian_acknowledged: bool
    participant_signature_png: str = Field(..., min_length=32, max_length=1_400_100)
    guardian_signature_png: str = Field(..., min_length=32, max_length=1_400_100)
    consent_version: str = Field(..., min_length=1, max_length=64)
    survey_version: str = Field(..., min_length=1, max_length=64)
    template_sha256: str = Field(..., pattern="^[0-9a-f]{64}$")
    idempotency_key: UUID

    @field_validator(
        "grade",
        "age_range",
        "pet_choice",
        "participant_printed_name",
        "guardian_printed_name",
    )
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("pet_choice")
    @classmethod
    def validate_pet_choice(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_PET_CHOICES:
            raise ValueError(f"pet_choice must be one of: {', '.join(sorted(VALID_PET_CHOICES))}")
        return normalized

    @field_validator("pin", "pin_confirmation")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("pin must contain only digits")
        return value

    @model_validator(mode="after")
    def validate_consent_submission(self) -> "ParticipantRegisterRequest":
        if self.pin != self.pin_confirmation:
            raise ValueError("PIN confirmation does not match")
        if not self.participant_acknowledged:
            raise ValueError("student acknowledgment is required")
        if not self.guardian_acknowledged:
            raise ValueError("guardian acknowledgment is required")
        return self


class ParticipantLoginRequest(BaseModel):
    public_id: str = Field(..., min_length=4, max_length=32)
    pin: str = Field(..., min_length=4, max_length=6)

    @field_validator("public_id")
    @classmethod
    def normalize_public_id(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("pin must contain only digits")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    public_id: str
    must_change_pin: bool = False


class ChangePinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)
    pin_confirmation: str = Field(..., min_length=4, max_length=6)

    @field_validator("pin", "pin_confirmation")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("pin must contain only digits")
        return value

    @model_validator(mode="after")
    def validate_match(self) -> "ChangePinRequest":
        if self.pin != self.pin_confirmation:
            raise ValueError("PIN confirmation does not match")
        return self


class ParticipantProfile(BaseModel):
    public_id: str
    grade: str
    age_range: str
    age_consent_category: str | None = None
    pet_choice: str

    model_config = {"from_attributes": True}


class RegisterResponse(TokenResponse):
    participant: ParticipantProfile


class RecentParticipantStatusRequest(BaseModel):
    public_ids: list[str] = Field(default_factory=list)

    @field_validator("public_ids")
    @classmethod
    def normalize_ids(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            pid = value.strip().upper()
            if not pid or pid in seen:
                continue
            if len(pid) > 32 or not pid.startswith("NC-"):
                continue
            seen.add(pid)
            cleaned.append(pid)
            if len(cleaned) >= 20:
                break
        return cleaned


class RecentParticipantStatusItem(BaseModel):
    public_id: str
    recent_eligible: bool


class RecentParticipantStatusResponse(BaseModel):
    participants: list[RecentParticipantStatusItem]
