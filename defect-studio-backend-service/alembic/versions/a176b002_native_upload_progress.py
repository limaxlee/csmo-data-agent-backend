"""Persist native ZIP processing stages and counts."""
from alembic import op
import sqlalchemy as sa

revision = "a176b002"
down_revision = "a176b001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("native_train_uploads", sa.Column("progress", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("native_train_uploads", "progress")

