"""Ordered replay cursor, including inserts from an older API during rollout."""
import sqlalchemy as sa
from alembic import op

revision = "a122b006"
down_revision = "a122b005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("run_events", sa.Column("sequence", sa.BigInteger(), nullable=True))
    op.execute("""UPDATE run_events SET sequence = ordered.seq FROM
        (SELECT id, ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY created_at, id) AS seq
         FROM run_events) ordered WHERE run_events.id = ordered.id""")
    op.create_index("uq_run_events_run_sequence", "run_events", ["run_id", "sequence"], unique=True)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION studio_event_sequence() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          PERFORM id FROM runs WHERE id = NEW.run_id FOR UPDATE;
          SELECT COALESCE(MAX(sequence), 0) + 1 INTO NEW.sequence
            FROM run_events WHERE run_id = NEW.run_id;
          RETURN NEW;
        END $$""")
        op.execute("""CREATE TRIGGER studio_event_sequence BEFORE INSERT ON run_events
            FOR EACH ROW EXECUTE FUNCTION studio_event_sequence()""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER studio_event_sequence ON run_events")
        op.execute("DROP FUNCTION studio_event_sequence()")
    op.drop_index("uq_run_events_run_sequence", table_name="run_events")
    op.drop_column("run_events", "sequence")
