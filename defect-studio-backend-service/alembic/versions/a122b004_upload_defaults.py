"""Persist managed default group IDs independently of display names."""
import sqlalchemy as sa

from alembic import op

revision = "a122b004"
down_revision = "a122b003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("studio_upload_defaults",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("group_id", sa.String(128), nullable=False))


def downgrade():
    op.drop_table("studio_upload_defaults")

