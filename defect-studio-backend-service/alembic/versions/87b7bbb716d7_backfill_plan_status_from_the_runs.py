"""backfill plan status from what the runs did

plans.status has been "draft" on every row since the table existed, including
plans that trained a model and generated images. Nothing ever moved it: the
agent's plan events carry the settings and no status, so the column only ever
received the default.

The code now advances the status as train/infer events arrive, but that only
helps plans that run from here on. This fills in the ones already recorded,
from the events those runs left in this same database.

This is a data migration, which the migrations here otherwise avoid — #66 and
#68 deliberately left duplicate and orphaned rows for a human to resolve. The
difference is that nothing is being chosen or discarded: the status is derived
from evidence already in the table next door, and a wrong guess is not possible
because the events either exist or they do not.

Ordering matters. `executed` runs first and `confirmed` only touches rows still
left at "draft", so a plan that generated images does not get downgraded.

updated_at is deliberately left alone. It records when the plan last changed,
not when this correction ran, and bumping it would make every old plan look
freshly edited.

Revision ID: 87b7bbb716d7
Revises: 2787624e5465
Create Date: 2026-08-27 16:41:02.184073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87b7bbb716d7'
down_revision: Union[str, None] = '2787624e5465'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _plans_reaching(event_types: str) -> str:
    return f"""
        EXISTS (
            SELECT 1 FROM run_events re
            JOIN runs r ON r.id = re.run_id
            WHERE r.thread_id = plans.thread_id
              AND re.payload ->> 'plan_id' = plans.plan_id
              AND re.event_type IN ({event_types})
        )
    """


def upgrade() -> None:
    op.execute(
        "UPDATE plans SET status = 'executed' WHERE status = 'draft' AND "
        + _plans_reaching("'infer.completed'")
    )
    op.execute(
        "UPDATE plans SET status = 'confirmed' WHERE status = 'draft' AND "
        + _plans_reaching("'train.started', 'infer.started'")
    )


def downgrade() -> None:
    """Nothing to undo.

    Putting every plan back to "draft" would also flatten the ones the running
    code has advanced since, and "draft" was never a state these plans were
    actually in — it was the absence of one.
    """
