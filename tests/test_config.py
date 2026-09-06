import pytest
from pydantic import ValidationError

from app.config import Settings


def test_provider_postgres_url_uses_psycopg_driver() -> None:
    """Verify standard provider URLs are normalized for the installed driver."""
    settings = Settings(database_url="postgresql://user:pass@db.example/linkmint")

    assert settings.database_url.startswith("postgresql+psycopg://")


def test_non_postgres_url_is_rejected_outside_tests() -> None:
    """Verify development and production cannot accidentally run on SQLite."""
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite+pysqlite:///local.db", environment="production")


def test_production_requires_public_base_url() -> None:
    """Verify production cannot generate links from untrusted request hosts."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:pass@db.example/linkmint",
            environment="production",
        )


def test_public_base_url_must_be_an_origin() -> None:
    """Verify generated short links cannot inherit a configured path or query."""
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:pass@db.example/linkmint",
            public_base_url="https://go.example.com/prefix?source=bad",
            environment="production",
        )
