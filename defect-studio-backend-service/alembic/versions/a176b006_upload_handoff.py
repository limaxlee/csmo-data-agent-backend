"""Durable upload handoff and cooperative ZIP cancellation."""
from alembic import op
import sqlalchemy as sa

revision = "a176b006"
down_revision = "a176b005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("native_train_uploads", sa.Column("batch_total", sa.Integer(), nullable=True))
    op.add_column("native_train_uploads", sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE native_train_uploads SET batch_sealed=true WHERE status IN ('queued','processing','staged','done') "
               "AND (batch_id IS NULL OR lower(filename) LIKE '%.zip')")


def downgrade():
    op.drop_column("native_train_uploads", "cancel_requested")
    op.drop_column("native_train_uploads", "batch_total")
