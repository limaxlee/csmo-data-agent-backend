"""Bounded blocking I/O, independent of FastAPI's request thread limiter."""
from __future__ import annotations

import asyncio
from functools import partial

import anyio
from anyio.lowlevel import RunVar

_limiter: RunVar[anyio.CapacityLimiter] = RunVar('run_database_io_limiter')


async def run_blocking(function, *args, **kwargs):
    # RunVar is scoped to the event loop, including separate pytest loops.
    try:
        limiter = _limiter.get()
    except LookupError:
        limiter = anyio.CapacityLimiter(4)
        _limiter.set(limiter)
    task = asyncio.create_task(anyio.to_thread.run_sync(partial(function, *args, **kwargs), limiter=limiter))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        # A thread cannot be cancelled. Finish/close its session before releasing
        # a per-run lock or allowing shutdown to finish. Never detach a writer.
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not task.cancelled():
            # A failed write must stay a failure, even during cancellation.
            task.result()
        raise
