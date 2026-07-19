from pydantic import BaseModel, Field, field_validator


class ResearcherLoginRequest(BaseModel):
    invite_code: str = Field(..., min_length=1, max_length=128)

    @field_validator("invite_code")
    @classmethod
    def strip_code(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("invite_code must not be empty")
        return cleaned


class ResearcherLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "researcher"
    researcher_id: str
    display_name: str
