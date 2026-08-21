from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Workflix API"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_debug: bool = False
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    demo_mode: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_url: str
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_access_expires_minutes: int = Field(default=15, ge=1, le=1440)
    jwt_refresh_expires_days: int = Field(default=7, ge=1, le=90)

    cors_origins: str = "http://localhost:5173"
    file_storage_provider: Literal["local", "s3", "r2"] = "local"
    max_upload_size_mb: int = Field(default=25, ge=1, le=250)
    upload_directory: Path = Path("uploads")

    ai_provider: str = "gemini"
    ai_fallback_provider: str | None = "groq"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        return normalized

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
