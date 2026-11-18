"""Seal durable image batches before worker publication."""
import sqlalchemy as sa
from alembic import op

revision = "a176b004"
down_revision = "a176b003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("native_train_uploads", sa.Column("batch_sealed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column("native_train_uploads", "batch_sealed")
