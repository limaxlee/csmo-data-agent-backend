"""Native multipart uploads and the per-thread input ownership marker."""
import sqlalchemy as sa
from alembic import op

revision = "a176b001"
down_revision = "a122b008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("native_train_inputs",
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("native_train_uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), sa.ForeignKey("threads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_key", sa.Uuid(), unique=True, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("multipart_id", sa.String(500), nullable=False),
        sa.Column("part_size", sa.Integer(), nullable=False),
        sa.Column("linked_file_id", sa.Uuid(), nullable=True),
        sa.Column("expected_mask_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("completed", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(100), nullable=True),
        sa.Column("cleaned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_native_train_uploads_thread_id", "native_train_uploads", ["thread_id"])
    op.create_index("ix_native_train_uploads_status", "native_train_uploads", ["status"])
    op.create_table("native_run_dispatches",
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("runs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("request_key", sa.Uuid(), unique=True, nullable=False),
        sa.Column("dispatch_started", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    op.drop_table("native_run_dispatches")
    op.drop_table("native_train_uploads")
    op.drop_table("native_train_inputs")

