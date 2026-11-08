import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from urllib.error import HTTPError

from aitrace_sdk import Trace
from aitrace_sdk.exporter import HttpExporter


class ExporterEventTests(unittest.TestCase):
    def test_trace_becomes_trace_event_and_span_events(self):
        trace = Trace("demo")
        with trace.span("retrieve", "RETRIEVAL"):
            pass
        trace.finish()

        events = trace.to_events("project-1")

        self.assertEqual(2, len(events))
        self.assertEqual("TRACE", events[0]["event_type"])
        self.assertEqual("SPAN", events[1]["event_type"])
        self.assertEqual("project-1", events[1]["project_id"])
        self.assertEqual(trace.id, events[1]["trace_id"])
        self.assertEqual(trace.spans[0].id, events[1]["span_id"])
        self.assertNotIn("id", events[1])

    def test_trace_does_not_send_evaluation_content_by_default(self):
        trace = Trace("demo")
        self.assertIsNone(trace.evaluation_payload)

    @patch("aitrace_sdk.exporter.urlopen")
    def test_http_400_prints_server_response_and_does_not_retry(self, urlopen):
        urlopen.side_effect = HTTPError(
            "http://localhost:8080/api/v1/telemetry/batches",
            400,
            "Bad Request",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"event_id is required"}'),
        )
        exporter = HttpExporter(
            "http://localhost:8080/api/v1/telemetry/batches",
            "project-1",
            max_retries=3,
        )
        output = io.StringIO()

        try:
            with redirect_stderr(output):
                exporter._send([{"event_id": "event-1"}])
        finally:
            exporter.shutdown()

        self.assertEqual(1, urlopen.call_count)
        self.assertIn("event_id is required", output.getvalue())
