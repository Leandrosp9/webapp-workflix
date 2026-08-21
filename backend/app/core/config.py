from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
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
    s3_bucket: str | None = None
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_force_path_style: bool = False
    s3_server_side_encryption: Literal["AES256", "aws:kms"] | None = None
    s3_kms_key_id: str | None = None

    rate_limit_provider: Literal["memory", "redis"] = "memory"
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    rate_limit_login_per_minute: int = Field(default=10, ge=1, le=10_000)
    rate_limit_refresh_per_minute: int = Field(default=30, ge=1, le=10_000)
    rate_limit_ai_per_minute: int = Field(default=10, ge=1, le=10_000)
    trust_proxy_headers: bool = False

    secrets_manager_provider: Literal["env", "aws"] = "env"
    aws_secret_id: str | None = None
    aws_region: str = "us-east-1"
    aws_secrets_endpoint_url: str | None = None

    ai_provider: str = "gemini"
    ai_fallback_provider: str | None = "groq"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    rag_embedding_model: str = "gemini-embedding-2"
    rag_embedding_dimensions: int = Field(default=768, ge=768, le=768)
    rag_max_pdf_pages: int = Field(default=500, ge=1, le=5000)
    rag_retrieval_limit: int = Field(default=6, ge=1, le=12)
    document_worker_poll_seconds: float = Field(default=1.0, ge=0.1, le=60)
    document_job_lease_seconds: int = Field(default=120, ge=30, le=3600)
    document_job_heartbeat_seconds: int = Field(default=30, ge=5, le=300)
    document_job_max_attempts: int = Field(default=5, ge=1, le=20)
    document_job_retry_base_seconds: int = Field(default=10, ge=1, le=3600)
    document_job_retry_max_seconds: int = Field(default=300, ge=1, le=86_400)
    groq_api_key: SecretStr | None = None
    groq_model: str | None = None

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/"):
            raise ValueError("api_v1_prefix must start with '/'")
        return normalized

    @field_validator("s3_server_side_encryption", mode="before")
    @classmethod
    def empty_optional_value_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_provider_configuration(self) -> "Settings":
        if self.file_storage_provider in {"s3", "r2"} and not self.s3_bucket:
            raise ValueError("s3_bucket is required for S3-compatible storage")
        if self.s3_server_side_encryption == "aws:kms" and not self.s3_kms_key_id:
            raise ValueError("s3_kms_key_id is required when using aws:kms encryption")
        if self.secrets_manager_provider == "aws" and not self.aws_secret_id:
            raise ValueError("aws_secret_id is required for AWS Secrets Manager")
        if self.document_job_heartbeat_seconds >= self.document_job_lease_seconds:
            raise ValueError("document_job_heartbeat_seconds must be shorter than the lease")
        if self.document_job_retry_base_seconds > self.document_job_retry_max_seconds:
            raise ValueError("document job retry base cannot exceed the retry maximum")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    from app.core.secrets import load_managed_secrets

    load_managed_secrets()
    return Settings()  # type: ignore[call-arg]
