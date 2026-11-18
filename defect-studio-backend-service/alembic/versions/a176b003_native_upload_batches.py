"""Group native direct uploads into atomic batches."""
import sqlalchemy as sa
from alembic import op

revision = "a176b003"
down_revision = "a176b002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("native_train_uploads", sa.Column("batch_id", sa.Uuid(), nullable=True))
    op.create_index("ix_native_train_uploads_batch_id", "native_train_uploads", ["batch_id"])


def downgrade():
    op.drop_index("ix_native_train_uploads_batch_id", table_name="native_train_uploads")
    op.drop_column("native_train_uploads", "batch_id")
