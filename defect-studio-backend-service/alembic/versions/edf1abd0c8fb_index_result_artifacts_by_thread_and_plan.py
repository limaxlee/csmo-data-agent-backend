"""index result_artifacts by thread and plan

Every read of result_artifacts filters on thread_id — on its own for the whole
gallery, with plan_id for one plan's images — and never on plan_id alone. The
only index was on plan_id, whose values are "0", "1", "2": a handful of distinct
keys across the entire table. Measured on a 1M-row copy of this schema, the
gallery query went 123ms (sequential scan) to 0.15ms with the composite index.

The unique constraint is what makes registration safe to run twice at once.
ResultArtifactRegistrar checks for an existing row and then inserts, and that
pair is not atomic; the event hook and the reconciliation backstop can both pass
the check for the same file.

Both statements take ACCESS EXCLUSIVE on result_artifacts. That is nothing at
today's size (5 rows), but on a large table it blocks writes for the duration —
CREATE INDEX CONCURRENTLY, outside a transaction, is the tool for that case.

Fails if duplicate (thread_id, plan_id, filename) rows already exist. Check
first, and decide which row to keep — that is not a migration's call to make:

    SELECT thread_id, plan_id, filename, count(*)
    FROM result_artifacts GROUP BY 1, 2, 3 HAVING count(*) > 1;

Revision ID: edf1abd0c8fb
Revises: 03049efb0278
Create Date: 2026-08-27 11:11:25.861320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edf1abd0c8fb'
down_revision: Union[str, None] = '03049efb0278'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('ix_result_artifacts_plan_id', table_name='result_artifacts')
    op.create_index(
        'ix_result_artifacts_thread_plan', 'result_artifacts',
        ['thread_id', 'plan_id'], unique=False,
    )
    op.create_unique_constraint(
        'uq_result_artifacts_thread_plan_filename', 'result_artifacts',
        ['thread_id', 'plan_id', 'filename'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_result_artifacts_thread_plan_filename', 'result_artifacts', type_='unique',
    )
    op.drop_index('ix_result_artifacts_thread_plan', table_name='result_artifacts')
    op.create_index(
        'ix_result_artifacts_plan_id', 'result_artifacts', ['plan_id'], unique=False,
    )
