"""Composition root for the background run-event consumer.

Builds the singleton RunConsumerManager with session-per-event persistence:
a training run can last hours, so no DB session or connection may live as
long as its consumer task does.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import logging
from typing import Any, AsyncIterator, Iterator
import uuid

from src.plan.infrastructure.adapters.repositories.plan_repository_adapter import PlanRepositoryAdapter
from src.plan.infrastructure.repositories.plan_repository_impl import PlanRepositoryImpl
from src.result.application.services import ResultArtifactRegistrar
from src.result.infrastructure.adapters.repositories.result_artifact_repository_adapter import ResultArtifactRepositoryAdapter
from src.result.infrastructure.repositories.result_artifact_repository_impl import ResultArtifactRepositoryImpl
from src.run.application.ports.out.gateways import AgentGateway
from src.run.application.services import (
    RunConsumerManager,
    RunEventBroker,
    RunEventRecorder,
    RunQueue,
    TrainingSlotQueue,
    classify_resumed_run_slot_state,
)
from src.run.infrastructure.adapters.repositories.run_event_repository_adapter import RunEventRepositoryAdapter
from src.run.infrastructure.adapters.repositories.run_repository_adapter import RunRepositoryAdapter
from src.run.infrastructure.repositories.run_event_repository_impl import RunEventRepositoryImpl
from src.run.infrastructure.repositories.run_repository_impl import RunRepositoryImpl
from src.thread.infrastructure.adapters.repositories.message_repository_adapter import MessageRepositoryAdapter
from src.thread.infrastructure.adapters.repositories.thread_repository_adapter import ThreadRepositoryAdapter
from src.thread.infrastructure.entity.thread_entity import MessageEntity
from src.thread.infrastructure.repositories.message_repository_impl import MessageRepositoryImpl
from src.thread.infrastructure.repositories.thread_repository_impl import ThreadRepositoryImpl
from src.container.database.engine import SessionLocal
from src.container.infrastructure import get_agent_service, get_event_processor, get_storage
from src.common.blocking_io import run_blocking

logger = logging.getLogger(__name__)


class _AgentServiceProxy(AgentGateway):
    """Resolves the agent gateway per call, so test overrides installed after
    the manager singleton was built (or swapped between tests) still apply."""

    async def start_run(self, thread_id: str, message: str) -> dict[str, Any]:
        return await get_agent_service().start_run(thread_id, message)

    async def stream_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        async for event in get_agent_service().stream_events(run_id):
            yield event

    async def submit_input(self, run_id: str, message: str) -> dict[str, Any]:
        return await get_agent_service().submit_input(run_id, message)

    async def cancel_run(self, run_id: str, reason: str = "user_cancelled") -> dict[str, Any]:
        return await get_agent_service().cancel_run(run_id, reason)

    async def get_run_status(self, run_id: str) -> dict[str, Any]:
        return await get_agent_service().get_run_status(run_id)


@contextmanager
def _recorder_scope() -> Iterator[RunEventRecorder]:
    db = SessionLocal()
    try:
        yield RunEventRecorder(
            RunRepositoryAdapter(RunRepositoryImpl(db)),
            RunEventRepositoryAdapter(RunEventRepositoryImpl(db)),
            MessageRepositoryAdapter(MessageRepositoryImpl(db)),
            PlanRepositoryAdapter(PlanRepositoryImpl(db)),
            _AgentServiceProxy(),
            get_event_processor(),
            ResultArtifactRegistrar(
                ThreadRepositoryAdapter(ThreadRepositoryImpl(db)),
                ResultArtifactRepositoryAdapter(ResultArtifactRepositoryImpl(db)),
                get_storage(),
            ),
        )
    finally:
        db.close()


_broker = RunEventBroker()
_manager: RunConsumerManager | None = None
_queue: RunQueue | None = None
_training_queue: TrainingSlotQueue | None = None


async def _release_training_slot(run_id) -> None:
    if _training_queue is not None:
        await _training_queue.release(run_id)


def get_run_event_broker() -> RunEventBroker:
    return _broker


def get_run_consumer_manager() -> RunConsumerManager:
    global _manager
    if _manager is None:
        from src.container.settings import get_settings

        _manager = RunConsumerManager(
            agent_service=_AgentServiceProxy(),
            broker=_broker,
            recorder_factory=_recorder_scope,
            stall_timeout=get_settings().run_stall_timeout_seconds,
            confirmation_timeout=get_settings().run_confirmation_timeout_seconds,
            input_wait_timeout=get_settings().run_input_wait_timeout_seconds,
            on_slot_released=_release_training_slot,
        )
    return _manager


def get_training_slot_queue() -> TrainingSlotQueue:
    """Return the singleton training-slot queue capping concurrent executions."""
    global _training_queue
    manager = get_run_consumer_manager()
    if (
        _training_queue is None
        or _training_queue._broker is not _broker
        or _training_queue._slot_queued != manager.slot_queued
    ):
        from src.container.settings import get_settings

        _training_queue = TrainingSlotQueue(
            agent_service=_AgentServiceProxy(),
            run_repo_factory=_run_repo_scope,
            event_repo_factory=_event_repo_scope,
            broker=_broker,
            max_slots=get_settings().max_concurrent_trainings,
            slot_queued=manager.slot_queued,
            input_submitted=manager.input_submitted,
            before_dispatch=_check_queued_input_guard,
            is_run_live=manager.is_active,
        )
    return _training_queue


def get_run_queue() -> RunQueue:
    """Return the singleton run queue, creating it on first call.

    The queue is wired here (not in dependencies.py) because it is a process
    singleton: every ``StartRunHandler`` must share the same semaphore so the
    Nth+1 request actually waits rather than each handler getting its own
    unlimited slot.
    """
    global _queue
    if _queue is None:
        from src.container.settings import get_settings

        _queue = RunQueue(
            agent_service=_AgentServiceProxy(),
            run_repo_factory=_run_repo_scope,
            thread_repo_factory=_thread_repo_scope,
            consumer=get_run_consumer_manager(),
            broker=_broker,
            max_concurrent=get_settings().max_concurrent_runs,
            before_dispatch=_check_input_snapshot,
            dispatch_failure=_record_dispatch_failure,
        )
    return _queue


def _check_input_snapshot(run) -> bool:
    """Fence crash-resumed queued runs before dispatching to Agent."""
    from src.train_data.infrastructure.native_dispatch import claim_dispatch

    with SessionLocal() as db:
        return claim_dispatch(db, run)


def _record_dispatch_failure(run, error):
    from src.train_data.infrastructure.native_dispatch import record_dispatch_failure

    with SessionLocal() as db:
        record_dispatch_failure(db, run, error, _broker)


def _check_queued_input_guard(run) -> None:
    from src.train_data.infrastructure.native_run_guard import NativeRunGuard

    with SessionLocal() as db:
        NativeRunGuard(db).check(run.thread_id.value, run.user_id.value)


def _resolve_queued_user_message(
    db, thread_id: uuid.UUID, payload: dict[str, Any] | None
) -> str | None:
    msg_id = (payload or {}).get("user_message_id")
    if msg_id:
        try:
            entity = db.get(MessageEntity, uuid.UUID(str(msg_id)))
            if entity is not None and entity.thread_id == thread_id:
                return entity.content
        except ValueError:
            pass
    latest = (
        db.query(MessageEntity)
        .filter_by(thread_id=thread_id, role="user")
        .order_by(MessageEntity.created_at.desc())
        .first()
    )
    return latest.content if latest is not None else None


@contextmanager
def _run_repo_scope() -> Iterator[RunRepositoryAdapter]:
    db = SessionLocal()
    try:
        yield RunRepositoryAdapter(RunRepositoryImpl(db))
    finally:
        db.close()


@contextmanager
def _event_repo_scope() -> Iterator[RunEventRepositoryAdapter]:
    db = SessionLocal()
    try:
        yield RunEventRepositoryAdapter(RunEventRepositoryImpl(db))
    finally:
        db.close()


@contextmanager
def _thread_repo_scope() -> Iterator[ThreadRepositoryAdapter]:
    db = SessionLocal()
    try:
        yield ThreadRepositoryAdapter(ThreadRepositoryImpl(db))
    finally:
        db.close()


async def resume_consumers() -> None:
    """Re-attach consumers and restore training-slot ownership after BFF restart.

    Active post-confirmation runs claim their slots before any queued inputs or
    initial runs are dispatched, preserving the global concurrency ceiling across
    restarts.
    """
    manager = get_run_consumer_manager()
    training_queue = get_training_slot_queue()

    def read_runs():
        with SessionLocal() as db:
            return [
                run
                for run in RunRepositoryAdapter(RunRepositoryImpl(db)).list_non_terminal()
                if run.status != "queued"
            ]

    runs = await run_blocking(read_runs)
    pending_waiters: list[tuple[Any, Any, str]] = []

    for run in runs:
        await manager._finalize(run)
        if run.is_terminal():
            continue

        def classify(target_run=run):
            with SessionLocal() as db:
                events = RunEventRepositoryAdapter(RunEventRepositoryImpl(db)).snapshot(
                    target_run.id
                )
                state, queued_ev = classify_resumed_run_slot_state(events)
                msg_text = None
                if state == "slot_queued" and queued_ev is not None:
                    msg_text = _resolve_queued_user_message(
                        db, target_run.thread_id.value, queued_ev.payload
                    )
                return state, queued_ev, msg_text

        state, queued_ev, msg_text = await run_blocking(classify)
        if state == "terminal":
            continue
        logger.info("Resuming consumer for run %s (slot_state=%s)", run.id, state)
        manager.ensure_started(run)
        if state == "active":
            training_queue.restore_active(run.id)
        elif state == "slot_queued" and queued_ev is not None and msg_text:
            pending_waiters.append((run, queued_ev, msg_text))

    pending_waiters.sort(key=lambda item: item[1].created_at or item[0].started_at)
    for run, queued_ev, msg_text in pending_waiters:
        payload = queued_ev.payload or {}
        submitted_raw = payload.get("submitted_at")
        submitted_at = (
            datetime.fromisoformat(submitted_raw)
            if isinstance(submitted_raw, str)
            else (queued_ev.created_at or run.started_at)
        )
        training_queue.restore_waiter(
            run,
            msg_text,
            submitted_at,
            user_message_id=payload.get("user_message_id"),
            notified_position=payload.get("queue_position"),
        )
    training_queue.kick()

    queue = get_run_queue()
    await queue.resume_queued()


async def shutdown_consumers() -> None:
    if _training_queue is not None:
        await _training_queue.shutdown()
    if _queue is not None:
        await _queue.shutdown()
    if _manager is not None:
        await _manager.shutdown()
