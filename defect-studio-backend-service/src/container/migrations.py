"""Startup check that the database is at the migration the code expects.

The app no longer creates tables; Alembic does. That trade needs a loud failure
mode, because a missed `alembic upgrade head` is otherwise invisible until a
query hits a column that does not exist yet.

This only warns. Refusing to start would be defensible, but it would also take
the service down for a schema difference that may not affect the request being
served, and there is no rollback path in the current deployment.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: alembic.ini lives at the repository root, two levels above this file.
_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def warn_if_migrations_pending() -> None:
    """Log where the database stands relative to the migration history."""
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        from src.container.database.engine import engine

        script = ScriptDirectory.from_config(Config(str(_ALEMBIC_INI)))
        head = script.get_current_head()

        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
    except Exception as e:  # noqa: BLE001 — a broken check must not stop startup
        logger.warning("Could not check database migration state: %s", e)
        return

    if current == head:
        logger.info("Database is at migration %s", current)
    elif current is None:
        logger.warning(
            "Database has no migration history. A new database needs "
            "`alembic upgrade head`; one that predates Alembic needs "
            "`alembic stamp head` first, or upgrade will fail on tables that "
            "already exist.",
        )
    else:
        logger.warning(
            "Database is at migration %s but the code expects %s. "
            "Run `alembic upgrade head`.",
            current, head,
        )

