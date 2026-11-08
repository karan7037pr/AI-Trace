"""Ask questions against the Virat Kohli vector database."""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from aitrace_sdk import HttpExporter
from app.vector_rag import PostgresVectorStore, ask_vector_rag


def send_evaluation_job(endpoint: str, project_id: str, trace_id: str, payload: dict) -> None:
    """Send opt-in full-content data to the protected evaluation job endpoint."""

    body = json.dumps({
        "project_id": project_id,
        "trace_id": trace_id,
        **payload,
    }).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            if response.status not in {200, 202}:
                raise RuntimeError(f"evaluation service returned HTTP {response.status}")
    except (HTTPError, URLError, TimeoutError, RuntimeError) as error:
        print(f"AITrace evaluation job was not submitted: {error}", file=sys.stderr)


def main() -> None:
    """Run one question through vector retrieval and answer generation."""

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        raise SystemExit('Usage: python3 -m app.ask "your question"')

    answer, trace = ask_vector_rag(question, PostgresVectorStore())

    telemetry_url = os.getenv("AITRACE_INGESTION_URL")
    if telemetry_url:
        exporter = HttpExporter(
            endpoint=telemetry_url,
            project_id=os.getenv("AITRACE_PROJECT_ID", "local-project"),
        )
        exporter.export_trace(trace)
        exporter.shutdown()

    evaluation_url = os.getenv("AITRACE_EVALUATION_URL")
    if evaluation_url and trace.evaluation_payload:
        send_evaluation_job(
            evaluation_url,
            os.getenv("AITRACE_PROJECT_ID", "local-project"),
            trace.id,
            trace.evaluation_payload,
        )

    print(f"Answer: {answer}\n")
    print("Trace:")
    print(json.dumps(trace.to_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
