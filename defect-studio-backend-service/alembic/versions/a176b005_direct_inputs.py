"""Direct final inputs and deferred thumbnails."""
from alembic import op
import sqlalchemy as sa

revision = "a176b005"
down_revision = "a176b004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("native_train_uploads", sa.Column("target_key", sa.String(500), nullable=True))
    op.add_column("train_data_files", sa.Column("thumbnail_status", sa.String(20), nullable=True))
    op.add_column("train_data_files", sa.Column("thumbnail_attempts", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("train_data_files", "thumbnail_attempts")
    op.drop_column("train_data_files", "thumbnail_status")
    op.drop_column("native_train_uploads", "target_key")

