from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load application configuration from environment variables or `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/url_shortener"
    public_base_url: AnyHttpUrl | None = None
    cors_origins: str = ""
    environment: Literal["development", "testing", "production"] = "development"
    link_creation_limit: int = Field(default=20, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)

    @field_validator("database_url")
    @classmethod
    def select_psycopg_driver(cls, value: str) -> str:
        """Normalize provider URLs to SQLAlchemy's Psycopg 3 driver scheme."""
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("public_base_url")
    @classmethod
    def require_origin_only(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        """Keep generated short links on a clean origin without a path or query."""
        if value and (value.path not in {None, "/"} or value.query or value.fragment):
            raise ValueError("PUBLIC_BASE_URL must contain only a scheme and host")
        return value

    @model_validator(mode="after")
    def require_postgres_outside_tests(self) -> "Settings":
        """Reject unsafe database or public URL settings outside automated tests."""
        if self.environment != "testing" and not self.database_url.startswith(
            ("postgresql://", "postgresql+psycopg://")
        ):
            raise ValueError("DATABASE_URL must use PostgreSQL")
        if self.environment == "production" and self.public_base_url is None:
            raise ValueError("PUBLIC_BASE_URL is required in production")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        """Return the configured comma-separated CORS origins as a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def load_settings() -> Settings:
    """Build validated settings for the current process environment."""
    return Settings()
