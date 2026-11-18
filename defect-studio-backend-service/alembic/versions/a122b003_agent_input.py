"""Durable Agent input preparation and run provenance, without changing Agent."""
import sqlalchemy as sa

from alembic import op

revision = "a122b003"
down_revision = "a122b002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("agent_input_preparations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_key", sa.Uuid(), unique=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("selection", sa.JSON(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("credential", sa.Text()),
        sa.Column("error", sa.String(100)),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_agent_input_preparations_thread_id", "agent_input_preparations", ["thread_id"])
    op.create_table("agent_input_runs",
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("preparation_id", sa.Uuid(), sa.ForeignKey("agent_input_preparations.id"), nullable=False))


def downgrade():
    op.drop_table("agent_input_runs")
    op.drop_table("agent_input_preparations")
