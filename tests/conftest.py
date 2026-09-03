from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.main import create_app
from app.models import Base


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Provide an isolated in-memory SQLAlchemy engine for each test."""
    test_engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def settings() -> Settings:
    """Provide explicit test-only configuration without production secrets."""
    return Settings(
        database_url="sqlite+pysqlite://",
        environment="testing",
    )


@pytest.fixture
def client(engine: Engine, settings: Settings) -> Iterator[TestClient]:
    """Provide an isolated FastAPI test client with migrated-style tables."""
    application = create_app(settings=settings, engine=engine)
    with TestClient(application) as test_client:
        yield test_client

