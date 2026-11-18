"""One Labeler Dataset per Thread, split by defect/ and normal/ folders.

Threads used to bind one Dataset per tab. Labeler now imports a Studio ZIP into
a single Dataset with role folders and paired masks, so the binding loses its
category. Existing bindings and upload records were test-only data on separate
per-tab Datasets that the new layout cannot read, so they are discarded rather
than migrated; affected Threads get a fresh default Dataset on next use.
"""
import sqlalchemy as sa
from alembic import op

revision = "a122b007"
down_revision = "a122b006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM labeler_upload_links")
    op.drop_table("labeler_dataset_bindings")
    op.create_table("labeler_dataset_bindings",
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    op.drop_table("labeler_dataset_bindings")
    op.create_table("labeler_dataset_bindings",
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category", sa.String(10), primary_key=True),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"))

