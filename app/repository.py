from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models import Link


class LinkRepository:
    """Read and write shortened links through one database session."""

    def __init__(self, session: Session) -> None:
        """Keep the request-scoped SQLAlchemy session."""
        self.session = session

    def insert(self, short_code: str, target_url: str) -> bool:
        """Insert a link and return false when its code already exists."""
        self.session.add(Link(short_code=short_code, target_url=target_url))
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            return False
        return True

    def get_target(self, short_code: str) -> str | None:
        """Return the destination of an active, unexpired link when present."""
        statement = select(Link.target_url).where(
            Link.short_code == short_code,
            Link.is_active.is_(True),
            or_(Link.expires_at.is_(None), Link.expires_at > func.now()),
        )
        return self.session.scalar(statement)

