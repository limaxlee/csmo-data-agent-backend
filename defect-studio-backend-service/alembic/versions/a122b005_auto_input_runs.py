"""Idempotent automatic input runs and durable dispatch fencing."""
import sqlalchemy as sa

from alembic import op

revision = "a122b005"
down_revision = "a122b004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_input_runs", sa.Column("request_key", sa.Uuid(), nullable=True))
    op.create_index("uq_agent_input_runs_request_key", "agent_input_runs", ["request_key"], unique=True)
    op.add_column("agent_input_runs", sa.Column("dispatch_started", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("agent_input_runs", "dispatch_started")
    op.drop_index("uq_agent_input_runs_request_key", table_name="agent_input_runs")
    op.drop_column("agent_input_runs", "request_key")

