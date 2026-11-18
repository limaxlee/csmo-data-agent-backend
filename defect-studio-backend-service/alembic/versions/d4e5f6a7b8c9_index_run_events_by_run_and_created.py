"""index run_events by (run_id, created_at)

The only read query on run_events filters by run_id and sorts by created_at
(``RunEventRepositoryImpl.list_by_run``). Neither column had an index — the
existing ``ix_run_events_event_type`` is never used as a filter in any query.
run_events is the largest table in the schema (one run produces ~4.6k rows),
and opening a conversation fires this query up to 30 times concurrently, each
doing a full table scan.

This migration adds a composite index ``ix_run_events_run_created`` on
(run_id, created_at) so a single index scan covers both the filter and the
sort.

Because run_events is the largest table, a plain ``CREATE INDEX`` would block
writes for the duration of the build — an in-flight run could not record its
events. ``CREATE INDEX CONCURRENTLY`` builds without taking an ACCESS
EXCLUSIVE lock, so it is safe to run while the app is live. PostgreSQL refuses
to run it inside a transaction, and env.py runs every migration inside one.
``autocommit_block()`` commits that transaction, runs the statement with
autocommit on, and then opens a new transaction for the remaining migrations.

On SQLite (the test database) ``CONCURRENTLY`` is a syntax error, so we fall
back to a regular ``CREATE INDEX`` there — SQLite locks the whole database
anyway, and the test fixtures create and drop tables per-test.

Revision ID: d4e5f6a7b8c9
Revises: a107b001
"""

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "a107b001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.create_index(
            "ix_run_events_run_created", "run_events",
            ["run_id", "created_at"], unique=False,
        )
    else:
        with op.get_context().autocommit_block():
            op.execute(
                "CREATE INDEX CONCURRENTLY ix_run_events_run_created "
                "ON run_events (run_id, created_at)"
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.drop_index("ix_run_events_run_created", table_name="run_events")
    else:
        with op.get_context().autocommit_block():
            op.execute("DROP INDEX CONCURRENTLY ix_run_events_run_created")

