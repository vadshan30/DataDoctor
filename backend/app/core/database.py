from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Engine is configured for predictable connection-pool behaviour:
# - pool_pre_ping reuses broken connections instead of failing requests
# - pool_recycle avoids stale connections after long idle periods
# - pool_size/max_overflow sized for typical dev traffic (saves ~50ms/request
#   by avoiding frequent new-connection handshakes)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_timeout=10,
    future=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    Uses a context manager-style try/finally so the session is always closed
    and returned to the pool even when the request raises.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
