"""Core in-memory tracing objects for AITrace milestone 1.

This module deliberately uses only Python's standard library.  It records data
in memory; sending data to an API will be a later milestone.
"""

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import uuid4


def _new_id() -> str:
    """Return a unique string identifier."""

    return str(uuid4())


def _now_iso() -> str:
    """Return the current UTC time in a JSON-friendly format."""

    return datetime.now(timezone.utc).isoformat()


class Span:
    """Represent one operation inside a trace, such as retrieval or generation."""

    def __init__(self, trace: "Trace", name: str, span_type: str, parent: "Span | None") -> None:
        self.trace = trace
        self.id = _new_id()
        self.name = name
        self.span_type = span_type
        self.parent_span_id = parent.id if parent else None
        self.start_time = _now_iso()
        self._started_clock = perf_counter()
        self.end_time: str | None = None
        self.duration_ms: float | None = None
        self.status = "RUNNING"
        self.error: str | None = None
        self.metadata: dict[str, Any] = {}

    def __enter__(self) -> "Span":
        """Allow ``with trace.span(...):`` to start a nested operation."""

        self.trace._active_spans.append(self)
        return self

    def __exit__(self, error_type: Any, error: Any, traceback: Any) -> bool:
        """Finish the span and record an exception, if the block raised one."""

        if error is not None:
            self.fail(str(error))
        else:
            self.finish()

        self.trace._active_spans.pop()
        return False

    def finish(self) -> None:
        """Mark a successful span as finished."""

        if self.end_time is not None:
            return

        self.end_time = _now_iso()
        self.duration_ms = round((perf_counter() - self._started_clock) * 1000, 3)
        self.status = "OK"

    def fail(self, message: str) -> None:
        """Mark a span as failed and save a human-readable error message."""

        if self.end_time is None:
            self.end_time = _now_iso()
            self.duration_ms = round((perf_counter() - self._started_clock) * 1000, 3)

        self.status = "ERROR"
        self.error = message

    def set_metadata(self, key: str, value: Any) -> None:
        """Attach structured information to the span."""

        self.metadata[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert this span into a JSON-serializable dictionary."""

        return {
            "id": self.id,
            "trace_id": self.trace.id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "type": self.span_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }


class Trace:
    """Represent one complete execution of a RAG application."""

    def __init__(self, name: str) -> None:
        self.id = _new_id()
        self.name = name
        self.start_time = _now_iso()
        self._started_clock = perf_counter()
        self.end_time: str | None = None
        self.duration_ms: float | None = None
        self.status = "RUNNING"
        self.error: str | None = None
        self.spans: list[Span] = []
        self._active_spans: list[Span] = []
        # Optional, short-lived content for an evaluation job. It is not part
        # of telemetry events and is populated only when sampling is enabled.
        self.evaluation_payload: dict[str, Any] | None = None

    def span(self, name: str, span_type: str) -> Span:
        """Create a span whose parent is the currently active span, if any."""

        parent = self._active_spans[-1] if self._active_spans else None
        new_span = Span(self, name, span_type, parent)
        self.spans.append(new_span)
        return new_span

    def finish(self) -> None:
        """Finish the trace and mark it successful."""

        if self.end_time is not None:
            return

        self.end_time = _now_iso()
        self.duration_ms = round((perf_counter() - self._started_clock) * 1000, 3)
        self.status = "OK"

    def fail(self, message: str) -> None:
        """Finish the trace as failed and save the error message."""

        if self.end_time is None:
            self.end_time = _now_iso()
            self.duration_ms = round((perf_counter() - self._started_clock) * 1000, 3)

        self.status = "ERROR"
        self.error = message

    def to_dict(self) -> dict[str, Any]:
        """Convert the complete trace into a JSON-serializable dictionary."""

        return {
            "id": self.id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error,
            "spans": [span.to_dict() for span in self.spans],
        }

    def to_events(self, project_id: str) -> list[dict[str, Any]]:
        """Convert this trace and its spans into telemetry events for the API."""

        events: list[dict[str, Any]] = [
            {
                "event_id": _new_id(),
                "event_type": "TRACE",
                "project_id": project_id,
                "trace_id": self.id,
                "span_id": None,
                "parent_span_id": None,
                "name": self.name,
                "type": None,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_ms": self.duration_ms,
                "status": self.status,
                "error": self.error,
                "metadata": {},
            }
        ]

        for span in self.spans:
            event = span.to_dict()
            # The in-memory span uses ``id`` for convenience, while the
            # telemetry API contract calls this field ``span_id``.
            event["span_id"] = event.pop("id")
            event["event_id"] = _new_id()
            event["event_type"] = "SPAN"
            event["project_id"] = project_id
            events.append(event)

        return events
