"""Application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Immutable application settings."""

    model_config = SettingsConfigDict(
        env_prefix="EW_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    app_name: str = Field(default="ElliottWaver")
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    timezone: str = "UTC"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
