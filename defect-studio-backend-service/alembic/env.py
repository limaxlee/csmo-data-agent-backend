"""Alembic environment — wired to the app's own metadata and settings.

The database URL comes from src.container.settings rather than alembic.ini, so
migrations always target the same database the app does and there is no second
place to keep credentials.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.container.database import db_types
from src.container.database.engine import Base
from src.container.settings import DatabaseSettings

# Imported for the side effect: without every entity module loaded,
# Base.metadata is a partial schema and autogenerate would write a migration
# that drops the tables it cannot see.
import src.container.database.entities  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", DatabaseSettings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Render db_types.UUID as its SQLAlchemy impl, sa.Uuid.

    A migration is a historical record: it has to keep working after the app
    code moves on. Emitting ``src.container.database.db_types.UUID()`` would tie
    every migration to a module that may be renamed or deleted. The DDL is the
    same either way — db_types.UUID is a TypeDecorator whose impl is sa.Uuid.
    """
    if type_ == "type" and isinstance(obj, db_types.UUID):
        return "sa.Uuid()"
    return False


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of running it, for review or manual apply."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_item=render_item,
            # SQLite cannot ALTER most things in place; batch mode rewrites the
            # table instead. Harmless on Postgres, and the test database is SQLite.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
