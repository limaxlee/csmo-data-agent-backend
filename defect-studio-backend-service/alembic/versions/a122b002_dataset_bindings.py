"""Persist upload destinations independently of individual upload sessions."""
import sqlalchemy as sa

from alembic import op

revision = "a122b002"
down_revision = "a122b001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("labeler_dataset_bindings",
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category", sa.String(10), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    op.drop_table("labeler_dataset_bindings")
