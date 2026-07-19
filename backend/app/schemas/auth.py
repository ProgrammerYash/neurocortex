from pydantic import BaseModel, Field, field_validator

VALID_PET_CHOICES = frozenset({"fox", "owl", "cat", "dragon"})
VALID_AGE_CONSENT_CATEGORIES = frozenset({"under_18", "age_18_or_over"})


class ParticipantRegisterRequest(BaseModel):
    grade: str = Field(..., min_length=1, max_length=64)
    age_range: str = Field(..., min_length=1, max_length=32)
    age_consent_category: str | None = Field(default=None, pattern="^(under_18|age_18_or_over)$")
    pet_choice: str = Field(..., min_length=1, max_length=32)
    pin: str = Field(..., min_length=4, max_length=6)
    assent_acknowledged: bool | None = None
    parental_permission_status: str | None = Field(default=None, pattern="^(declined|pending)$")
    adult_consent_acknowledged: bool | None = None

    @field_validator("grade", "age_range", "pet_choice")
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

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("pin must contain only digits")
        return value


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


class ParticipantProfile(BaseModel):
    public_id: str
    grade: str
    age_range: str
    age_consent_category: str | None = None
    pet_choice: str

    model_config = {"from_attributes": True}


class RegisterResponse(TokenResponse):
    participant: ParticipantProfile
