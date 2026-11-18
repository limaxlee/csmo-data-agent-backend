"""Raw HTTP client for agent_service — no domain knowledge."""

from __future__ import annotations

import json
import logging
from contextlib import aclosing
from typing import Any, AsyncIterator

import httpx

from src.container.settings import get_settings
from src.common.agent_event_diagnostics import StreamDiagnostics

logger = logging.getLogger(__name__)
settings = get_settings()


class _DiagnosticByteStream(httpx.AsyncByteStream):
    """Observe raw HTTP body chunks without changing HTTPX decoding/framing."""

    def __init__(self, stream, diagnostics):
        self.stream, self.diagnostics = stream, diagnostics

    async def __aiter__(self):
        async for chunk in self.stream:
            self.diagnostics.raw_chunk(chunk)
            yield chunk
        self.diagnostics.transport_log("raw_eof", total_bytes=self.diagnostics.raw_bytes,
                                       chunk_count=self.diagnostics.raw_chunks)

    async def aclose(self):
        await self.stream.aclose()


class AgentHttpClient:
    """HTTP client for the internal DefectAgent agent_service API."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.agent_service_base_url

    async def start_run(self, thread_id: str, message: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"thread_id": thread_id, "message": message}
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/internal/agent/threads/{thread_id}/runs",
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def stream_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        diagnostics = StreamDiagnostics(
            run_id, transport_details=get_settings().agent_sse_transport_diagnostics,
        )
        outcome = "consumer_closed"
        try:
            async with aclosing(self._stream_events(run_id, diagnostics)) as stream:
                async for event in stream:
                    yield event
            outcome = "eof"
        except Exception as error:
            outcome = "error"
            diagnostics.log("stream_error", exception_type=type(error).__name__)
            raise
        finally:
            diagnostics.log(
                "stream_closed",
                outcome=outcome,
                event_count=diagnostics.events,
                line_count=diagnostics.lines,
                raw_chunk_count=diagnostics.raw_chunks,
                raw_byte_count=diagnostics.raw_bytes,
                pending_data_lines=diagnostics.pending_data_lines,
            )

    async def _stream_events(self, run_id, diagnostics):
        url = f"{self.base_url}/internal/agent/runs/{run_id}/events"
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", url, timeout=None) as resp:
                resp.raise_for_status()
                diagnostics.log(
                    "headers_received",
                    status_code=resp.status_code,
                    headers={
                        key: resp.headers[key]
                        for key in (
                            "content-type",
                            "content-encoding",
                            "cache-control",
                            "x-accel-buffering",
                        )
                        if key in resp.headers
                    },
                )
                event_type = None
                data_lines: list[str] = []
                if diagnostics.transport_details:
                    resp.stream = _DiagnosticByteStream(resp.stream, diagnostics)

                async for line in resp.aiter_lines():
                    diagnostics.line(line)
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                    elif line == "":
                        if data_lines:
                            raw = "\n".join(data_lines)
                            try:
                                event = json.loads(raw)
                            except json.JSONDecodeError:
                                event = {"type": event_type, "raw": raw}
                            yield diagnostics.event(event, dispatch_trigger="blank_line")
                        event_type = None
                        data_lines = []

                if data_lines:
                    raw = "\n".join(data_lines)
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        event = {"type": event_type, "raw": raw}
                    yield diagnostics.event(event, dispatch_trigger="eof")

    async def submit_input(self, run_id: str, message: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/internal/agent/runs/{run_id}/input",
                json={"message": message},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def cancel_run(self, run_id: str, reason: str = "user_cancelled") -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/internal/agent/runs/{run_id}/cancel",
                json={"reason": reason},
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_run_status(self, run_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/internal/agent/runs/{run_id}",
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()
