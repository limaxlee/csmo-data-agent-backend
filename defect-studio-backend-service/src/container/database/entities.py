"""Imports every entity module so ``Base.metadata`` describes the whole schema.

Mapped classes only register themselves when their module is imported, and a
partial registration is worse than an empty one: ``threads.user_id`` cannot
resolve its foreign key without ``users``, so metadata operations raise instead
of quietly doing less. Anything that reads the metadata as a whole — Alembic
autogenerate, the test suite's ``create_all`` — imports this module first.

Add new entity modules here.
"""

from __future__ import annotations

import src.auth.infrastructure.entity.user_entity  # noqa: F401
import src.plan.infrastructure.entity.plan_entity  # noqa: F401
import src.result.infrastructure.entity.result_entity  # noqa: F401
import src.run.infrastructure.entity.run_entity  # noqa: F401
import src.thread.infrastructure.entity.thread_entity  # noqa: F401
import src.train_data.infrastructure.entity.train_data_entity  # noqa: F401
import src.train_data.infrastructure.legacy_tables  # noqa: F401
import src.train_data.infrastructure.native_models  # noqa: F401
