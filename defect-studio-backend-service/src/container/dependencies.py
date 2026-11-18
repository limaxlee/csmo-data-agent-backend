"""Dependency Injection wiring — re-export façade for backward compatibility.

The actual providers now live in:
  - ``src.container.infrastructure``        — shared singletons + cross-context repo adapters
  - ``src.{context}.infrastructure.dependencies`` — per-context repo adapters + handler factories

This module re-exports everything so that existing imports
(``from src.container.dependencies import ...``) continue to work.

Controllers should migrate to importing from the per-context modules directly.
"""

from __future__ import annotations

# ── Shared infrastructure (singletons + override hooks + cross-context repos) ──
from src.container.infrastructure import (  # noqa: F401
    get_agent_service,
    get_event_processor,
    get_message_repo_adapter,
    get_password_hasher,
    get_storage,
    get_thread_repo_adapter,
    get_token_service,
    init_storage,
    reset_storage,
    set_agent_service_override,
)

# ── Auth Context ──
from src.auth.infrastructure.dependencies import (  # noqa: F401
    get_login_handler,
    get_refresh_token_handler,
    get_register_handler,
    get_user_repo_adapter,
)

# ── Thread Context ──
from src.thread.infrastructure.dependencies import (  # noqa: F401
    get_create_thread_handler,
    get_delete_thread_handler,
    get_thread_handler,
    get_list_messages_handler,
    get_list_threads_handler,
    get_update_thread_handler,
)

# ── Run Context ──
from src.run.infrastructure.dependencies import (  # noqa: F401
    get_cancel_run_handler,
    get_get_run_detail_handler,
    get_list_runs_handler,
    get_run_event_repo_adapter,
    get_run_repo_adapter,
    get_start_run_handler,
    get_stream_run_events_handler,
    get_submit_input_handler,
)

# ── Plan Context ──
from src.plan.infrastructure.dependencies import (  # noqa: F401
    get_get_plan_handler,
    get_list_plans_handler,
    get_plan_repo_adapter,
)

# ── Result Context ──
from src.result.infrastructure.dependencies import (  # noqa: F401
    get_get_result_file_handler,
    get_list_results_handler,
    get_register_artifact_handler,
    get_result_artifact_repo_adapter,
)

# ── Train Data Context ──
from src.train_data.infrastructure.dependencies import (  # noqa: F401
    get_delete_all_train_data_handler,
    get_delete_train_data_file_handler,
    get_get_train_data_file_handler,
    get_list_train_data_handler,
    get_train_data_repo_adapter,
    get_train_data_status_repo_adapter,
    get_upload_train_data_handler,
)

# ── DB session (re-exported for convenience) ──
from src.container.database.engine import get_db  # noqa: F401
