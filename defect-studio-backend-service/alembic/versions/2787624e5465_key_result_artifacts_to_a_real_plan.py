"""key result artifacts to a real plan

result_artifacts.plan_id named a row in plans, but nothing checked that the row
existed: the registrar copies the string out of an agent event and inserts it.
An artifact could point at a plan that was never recorded, and deleting a plan
left its images behind — only deleting the whole thread cleaned anything up.

The key between the two tables is the pair, not plan_id, which is "0" in nearly
every thread. So plans gets a unique constraint on its natural key — Postgres
needs one on the referenced columns anyway — and result_artifacts gets a
composite foreign key.

The unique constraint also settles a race. RunEventRecorder._save_plan looks for
an existing plan and inserts if it finds none, so two runs on the same thread
told about plan "0" can both insert.

Both statements take ACCESS EXCLUSIVE, and the foreign key scans
result_artifacts to validate existing rows. Instant at today's size; on a large
table, add the constraint NOT VALID and VALIDATE CONSTRAINT separately, which
takes only a SHARE UPDATE EXCLUSIVE lock.

Check before deploying — this fails if either query returns anything, and
neither cleanup is a migration's decision to make:

    -- plans that would collide
    SELECT thread_id, plan_id, count(*)
    FROM plans GROUP BY 1, 2 HAVING count(*) > 1;

    -- artifacts naming a plan that does not exist
    SELECT ra.thread_id, ra.plan_id, count(*)
    FROM result_artifacts ra
    WHERE NOT EXISTS (
        SELECT 1 FROM plans p
        WHERE p.thread_id = ra.thread_id AND p.plan_id = ra.plan_id
    )
    GROUP BY 1, 2;

Revision ID: 2787624e5465
Revises: edf1abd0c8fb
Create Date: 2026-08-27 13:06:06.079238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2787624e5465'
down_revision: Union[str, None] = 'edf1abd0c8fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_plans_thread_plan', 'plans', ['thread_id', 'plan_id'])
    op.create_foreign_key(
        'fk_result_artifacts_plan', 'result_artifacts', 'plans',
        ['thread_id', 'plan_id'], ['thread_id', 'plan_id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('fk_result_artifacts_plan', 'result_artifacts', type_='foreignkey')
    op.drop_constraint('uq_plans_thread_plan', 'plans', type_='unique')

