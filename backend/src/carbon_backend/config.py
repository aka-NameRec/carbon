"""Application configuration loaded from the environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for carbon-backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CARBON_",
        extra="ignore",
        validate_default=True,
    )

    database_dsn: str = "postgresql+psycopg://carbon@127.0.0.1:5433/carbon"
    vault_root: Path = Path("~/.my-links/logs-obsidian/carbon/Notifications")
    token_file: Path = Path("~/.config/carbon/tokens.json")
    bind_host: str = "127.0.0.1"
    bind_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    @field_validator("database_dsn")
    @classmethod
    def validate_database_dsn(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("database_dsn must use the postgresql+psycopg dialect")
        return value

    @field_validator("vault_root", "token_file")
    @classmethod
    def normalize_path(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("log_level must be a standard logging level")
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Return the cached process-wide settings instance."""

    return Settings()
