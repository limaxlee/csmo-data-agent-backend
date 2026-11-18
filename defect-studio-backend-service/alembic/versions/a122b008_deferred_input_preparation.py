"""Persist the dataset binding for preparation that waits for an import."""
import sqlalchemy as sa
from alembic import op

revision = "a122b008"
down_revision = "a122b007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("agent_input_preparations", sa.Column("source_binding", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("agent_input_preparations", "source_binding")
