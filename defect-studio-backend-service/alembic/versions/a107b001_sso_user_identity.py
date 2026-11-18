"""Add optional SSO identity and passwordless users.

Revision ID: a107b001
Revises: 87b7bbb716d7
"""

from alembic import op
import sqlalchemy as sa

revision = "a107b001"
down_revision = "87b7bbb716d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("sso_loginid", sa.String(255), nullable=True))
        batch.alter_column("password_hash", existing_type=sa.String(255), nullable=True)
        batch.create_unique_constraint("uq_users_sso_loginid", ["sso_loginid"])
    op.create_table(
        "sso_link_audit",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sso_loginid", sa.String(255), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("evidence_ref", sa.String(255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )


def downgrade() -> None:
    # A passwordless account cannot fit in the old schema. Resolve it before
    # downgrading instead of silently deleting users or inventing passwords.
    connection = op.get_bind()
    passwordless = connection.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE password_hash IS NULL")
    ).scalar_one()
    if passwordless:
        raise RuntimeError("Cannot downgrade while SSO-only users have no password hash")
    op.drop_table("sso_link_audit")
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("uq_users_sso_loginid", type_="unique")
        batch.alter_column("password_hash", existing_type=sa.String(255), nullable=False)
        batch.drop_column("sso_loginid")
