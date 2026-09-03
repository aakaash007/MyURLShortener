from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """Own the SQLAlchemy engine and request-scoped session factory."""

    def __init__(self, database_url: str, engine: Engine | None = None) -> None:
        """Create or accept an engine and configure reusable database sessions."""
        self.engine = engine or create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def sessions(self) -> Iterator[Session]:
        """Yield one database session and always close it after the request."""
        with self.session_factory() as session:
            yield session

    def is_ready(self) -> bool:
        """Return whether the database accepts a lightweight query."""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def dispose(self) -> None:
        """Release pooled database connections during application shutdown."""
        self.engine.dispose()

