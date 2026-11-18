"""SQLAlchemy engine and session setup."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from src.container.settings import DatabaseSettings

# Migrations need only database settings, without SSO or external services.
settings = DatabaseSettings()

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False, "timeout": 30},
        poolclass=NullPool,
        echo=settings.debug,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
else:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=settings.debug,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yield a database session and ensure it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
