"""Buffered HTTP exporter for the AITrace telemetry service."""

import json
import sys
import time
from queue import Empty, Queue
from threading import Thread
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .tracing import Trace


class HttpExporter:
    """Send telemetry without blocking the monitored application."""

    _STOP = object()

    def __init__(
        self,
        endpoint: str,
        project_id: str,
        max_batch_size: int = 20,
        flush_interval_seconds: float = 2.0,
        max_retries: int = 3,
    ) -> None:
        self.endpoint = endpoint
        self.project_id = project_id
        self.max_batch_size = max_batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self.max_retries = max_retries
        self._events: Queue[dict[str, Any] | object] = Queue()
        self._worker = Thread(target=self._run, name="aitrace-exporter", daemon=True)
        self._worker.start()

    def export_trace(self, trace: Trace) -> None:
        """Queue every event from a completed trace for export."""

        for event in trace.to_events(self.project_id):
            self._events.put(event)

    def shutdown(self) -> None:
        """Flush remaining events and stop the exporter worker."""

        self._events.put(self._STOP)
        self._worker.join(timeout=10)

    def _run(self) -> None:
        batch: list[dict[str, Any]] = []
        deadline: float | None = None

        while True:
            timeout = None if deadline is None else max(0, deadline - time.monotonic())
            try:
                item = self._events.get(timeout=timeout)
            except Empty:
                self._send(batch)
                batch = []
                deadline = None
                continue

            if item is self._STOP:
                if batch:
                    self._send(batch)
                return

            batch.append(item)
            if deadline is None:
                deadline = time.monotonic() + self.flush_interval_seconds

            if len(batch) >= self.max_batch_size:
                self._send(batch)
                batch = []
                deadline = None

    def _send(self, events: list[dict[str, Any]]) -> None:
        if not events:
            return

        payload = json.dumps({"project_id": self.project_id, "events": events}).encode("utf-8")
        request = Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=5) as response:
                    if response.status not in {200, 202}:
                        raise RuntimeError(f"telemetry service returned HTTP {response.status}")
                return
            except HTTPError as error:
                # HTTPError is also a file-like response. Reading its body is
                # important because the server usually explains which field
                # made the telemetry invalid (for example, a missing trace_id).
                try:
                    response_body = error.read().decode("utf-8", errors="replace").strip()
                except OSError:
                    response_body = ""

                message = f"{error}"
                if response_body:
                    message = f"{message} - response: {response_body[:1000]}"

                # A 4xx request is invalid and retrying the same payload will
                # not fix it. Drop it immediately and show the server reason.
                if 400 <= error.code < 500 and error.code != 429:
                    print(f"AITrace exporter dropped a batch: {message}", file=sys.stderr)
                    return

                if attempt == self.max_retries:
                    print(f"AITrace exporter dropped a batch: {message}", file=sys.stderr)
                    return
                time.sleep(0.2 * (attempt + 1))
            except (URLError, TimeoutError, RuntimeError) as error:
                if attempt == self.max_retries:
                    print(f"AITrace exporter dropped a batch: {error}", file=sys.stderr)
                    return
                time.sleep(0.2 * (attempt + 1))
