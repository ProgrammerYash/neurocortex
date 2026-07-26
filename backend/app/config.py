from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="SQLAlchemy PostgreSQL URL",
    )
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    environment: str = "development"
    api_prefix: str = "/v1"
    study_mode: Literal["development", "pilot", "production"] = Field(
        default="development",
        validation_alias="STUDY_MODE",
    )
    show_test_data: bool | None = Field(default=None, validation_alias="SHOW_TEST_DATA")
    allow_participant_predictions: bool | None = Field(
        default=None,
        validation_alias="ALLOW_PARTICIPANT_PREDICTIONS",
    )
    block_synthetic_prefixes: str = Field(
        default="MLSEED,MLPRED,MLSHAP",
        validation_alias="BLOCK_SYNTHETIC_PREFIXES",
    )
    synthetic_dataset_prefix: str = Field(
        default="phase-2",
        validation_alias="SYNTHETIC_DATASET_PREFIX",
    )
    require_consent_for_sessions: bool | None = Field(
        default=None,
        validation_alias="REQUIRE_CONSENT_FOR_SESSIONS",
    )
    active_study_protocol_version: str = Field(
        default="2026-pilot-v1",
        validation_alias="ACTIVE_STUDY_PROTOCOL_VERSION",
    )
    active_study_procedure_version: str = Field(
        default="2026-pilot-procedure-v1",
        validation_alias="ACTIVE_STUDY_PROCEDURE_VERSION",
    )
    allow_researcher_consent_override: bool = Field(
        default=False,
        validation_alias="ALLOW_RESEARCHER_CONSENT_OVERRIDE",
    )
    study_timezone: str = Field(
        default="America/New_York",
        validation_alias="STUDY_TIMEZONE",
    )
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str | None = Field(default=None, validation_alias="GROQ_MODEL")
    groq_timeout_seconds: int = Field(default=30, validation_alias="GROQ_TIMEOUT_SECONDS")
    groq_max_retries: int = Field(default=2, validation_alias="GROQ_MAX_RETRIES")
    smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, validation_alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, validation_alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")
    golden_vault_enabled: bool = Field(default=False, validation_alias="GOLDEN_VAULT_ENABLED")
    golden_vault_code_hash: str | None = Field(default=None, validation_alias="GOLDEN_VAULT_CODE_HASH")
    golden_vault_token_minutes: int = Field(default=30, validation_alias="GOLDEN_VAULT_TOKEN_MINUTES")
    golden_overrides_visible: bool = Field(default=True, validation_alias="GOLDEN_OVERRIDES_VISIBLE")

    @model_validator(mode="after")
    def apply_study_mode_defaults(self) -> "Settings":
        if self.show_test_data is None:
            self.show_test_data = self.study_mode == "development"
        if self.allow_participant_predictions is None:
            self.allow_participant_predictions = False
        if self.require_consent_for_sessions is None:
            self.require_consent_for_sessions = self.study_mode != "development"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
