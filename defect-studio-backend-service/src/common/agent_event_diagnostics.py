"""Payload-free diagnostics for upstream SSE delivery and persistence."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
QUIET_EVENTS = {
    "assistant.delta",
    "heartbeat",
    "agent.heartbeat",
    "train.log",
    "train.progress",
    "infer.progress",
}


def diagnostic_log(stage, **fields):
    level = logging.DEBUG if fields.get("event_type") in QUIET_EVENTS else logging.INFO
    logger.log(
        level,
        "Agent event diagnostic %s",
        json.dumps({"stage": stage, **fields}, default=str),
    )


class StreamDiagnostics:
    def __init__(self, run_id, transport_details=False):
        self.run_id = run_id
        self.connection_id = uuid.uuid4().hex
        self.started = time.monotonic()
        self.last_event = None
        self.last_source_time = None
        self.events = 0
        self.lines = 0
        self.transport_details = transport_details
        self.raw_chunks = 0
        self.raw_bytes = 0
        self.pending_data_lines = 0
        self.frame_started = None
        self.log("connect_start")

    def log(self, stage, **fields):
        diagnostic_log(
            stage,
            agent_run_id=self.run_id,
            connection_id=self.connection_id,
            elapsed_ms=round((time.monotonic() - self.started) * 1000, 3),
            **fields,
        )

    def raw_chunk(self, chunk):
        self.raw_chunks += 1
        self.raw_bytes += len(chunk)
        self.transport_log(
            "raw_chunk_received", chunk_index=self.raw_chunks,
            byte_count=len(chunk), total_bytes=self.raw_bytes,
            lf_count=chunk.count(b"\n"), cr_count=chunk.count(b"\r"),
            ends_with_lf=chunk.endswith(b"\n"),
            ends_with_double_lf=chunk.endswith(b"\n\n"),
            ends_with_cr=chunk.endswith(b"\r"),
        )

    def transport_log(self, stage, **fields):
        if self.transport_details:
            self.log(stage, observed_at=datetime.now(timezone.utc).isoformat(), **fields)

    def line(self, line=None):
        self.lines += 1
        if self.lines == 1:
            self.log("first_line")
        if line is None or not self.transport_details:
            return
        kind = ("blank" if line == "" else "data" if line.startswith("data:")
                else "comment" if line.startswith(":") else "event" if line.startswith("event:")
                else "other")
        if kind == "data":
            if self.frame_started is None:
                self.frame_started = time.monotonic()
            self.pending_data_lines += 1
        self.transport_log("line_received", line_index=self.lines, line_kind=kind,
                           char_count=len(line), pending_data_lines=self.pending_data_lines,
                           raw_chunk_index=self.raw_chunks)

    def event(self, event, dispatch_trigger=None):
        now = time.monotonic()
        received = datetime.now(timezone.utc)
        source = event.get("timestamp")
        source = source[:100] if isinstance(source, str) else None
        timestamp_status, lag_ms = "missing", None
        parsed = None
        if source:
            try:
                parsed = datetime.fromisoformat(source.replace("Z", "+00:00"))
                timestamp_status = "aware" if parsed.tzinfo else "timezone_unknown"
                if parsed.tzinfo:
                    lag_ms = round((received - parsed).total_seconds() * 1000, 3)
            except ValueError:
                timestamp_status = "invalid"
        source_gap_ms = None
        if parsed is not None and self.last_source_time is not None:
            if bool(parsed.tzinfo) == bool(self.last_source_time.tzinfo):
                source_gap_ms = round(
                    (parsed - self.last_source_time).total_seconds() * 1000, 3
                )
        self.last_source_time = parsed
        event_type = event.get("type")
        event_type = event_type[:80] if isinstance(event_type, str) else None
        identity = event.get("event_id")
        identity = identity[:100] if isinstance(identity, str) else None
        metadata = {
            "connection_id": self.connection_id,
            "agent_event_id": identity,
            "source_timestamp": source,
            "source_timestamp_status": timestamp_status,
            "received_at": received.isoformat(),
            "source_to_receive_ms": lag_ms,
            "event_index": self.events + 1,
            "source_gap_ms": source_gap_ms,
            "receive_gap_ms": round((now - self.last_event) * 1000, 3)
            if self.last_event is not None
            else None,
            "connection_elapsed_ms": round((now - self.started) * 1000, 3),
        }
        if self.transport_details:
            metadata.update(
                dispatch_trigger=dispatch_trigger,
                frame_wait_ms=round((now - self.frame_started) * 1000, 3)
                if self.frame_started is not None else None,
                frame_data_lines=self.pending_data_lines,
                raw_chunk_index=self.raw_chunks,
                line_index=self.lines,
            )
        self.frame_started = None
        self.pending_data_lines = 0
        self.events += 1
        self.last_event = now
        self.log(
            "event_received",
            event_type=event_type,
            **{k: v for k, v in metadata.items() if k != "connection_id"},
        )
        # Internal envelope field; the recorder copies it into persisted JSONB.
        # Never trust an upstream value for this field.
        return {**event, "_studio_transport": metadata}
