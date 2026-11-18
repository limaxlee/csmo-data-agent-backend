"""add mask_storage_key to result_artifacts

DefectAgent writes one black-and-white mask per generated image, under
``mask/infer/final_results/`` with the same filename as the image under
``defect/infer/final_results/``. The gallery needs the mask to draw it over the
image (train-service issue #110).

The mask is stored on the image's row, not as a row of its own. Both the
unique constraint ``uq_result_artifacts_thread_plan_filename`` and the
download route look a row up by (thread_id, plan_id, filename), and the image
and its mask have the same filename.

The column is nullable. Rows registered before this migration have no value
until ``backfill_results.py`` runs, and an image whose mask is missing from
storage keeps NULL.

Revision ID: d846574dcd45
Revises: d4e5f6a7b8c9
"""

import sqlalchemy as sa
from alembic import op

revision = "d846574dcd45"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "result_artifacts",
        sa.Column("mask_storage_key", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("result_artifacts", "mask_storage_key")
