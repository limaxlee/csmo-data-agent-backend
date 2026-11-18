"""Add Studio references to Labeler upload sessions (no cross-service FK)."""
import sqlalchemy as sa

from alembic import op

revision = "a122b001"
down_revision = "d846574dcd45"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "labeler_upload_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", sa.String(128), nullable=False),
        sa.Column("upload_id", sa.String(128), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("category", sa.String(10), nullable=False),
        sa.UniqueConstraint("dataset_id", "upload_id"),
    )
    op.create_index("ix_labeler_upload_links_thread_id", "labeler_upload_links", ["thread_id"])


def downgrade():
    op.drop_index("ix_labeler_upload_links_thread_id", table_name="labeler_upload_links")
    op.drop_table("labeler_upload_links")

