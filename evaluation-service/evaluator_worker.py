"""Consume sampled RAG jobs and store Jev evaluation scores."""

import json
import os
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import psycopg
from kafka import KafkaConsumer


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("AITRACE_EVALUATION_TOPIC", "aitrace.evaluation.jobs")
KAFKA_GROUP = os.getenv("AITRACE_EVALUATION_GROUP", "aitrace-jev-evaluator")
EVALUATION_PROVIDER = os.getenv("EVALUATION_PROVIDER", "jev").lower()
JEV_API_KEY = os.getenv("JEV_API_KEY")
JEV_API_URL = os.getenv("JEV_API_URL", "https://jeval.dev/api/v1/evaluate")
JEV_VERSION = os.getenv("JEV_EVALUATOR_VERSION", "jev-latest")
DATABASE_URL = os.getenv(
    "TELEMETRY_DATABASE_URL",
    "postgresql://telemetry:telemetry@localhost:5433/telemetry",
)


def require_configuration() -> None:
    if EVALUATION_PROVIDER != "jev":
        raise RuntimeError(f"Unsupported EVALUATION_PROVIDER: {EVALUATION_PROVIDER}")
    if not JEV_API_KEY:
        raise RuntimeError("JEV_API_KEY is missing. Export a rotated Jev key before starting the worker.")


def validate_job(job: dict[str, Any]) -> None:
    required = ("project_id", "trace_id", "input", "output", "context", "evaluators")
    missing = [field for field in required if not job.get(field)]
    if missing:
        raise ValueError(f"evaluation job is missing: {', '.join(missing)}")
    if not isinstance(job["context"], list) or not all(isinstance(item, str) for item in job["context"]):
        raise ValueError("evaluation context must be a list of strings")
    if not isinstance(job["evaluators"], list) or not job["evaluators"]:
        raise ValueError("evaluation evaluators must be a non-empty list")


def call_jev(job: dict[str, Any]) -> dict[str, Any]:
    request_body = {
        "evaluators": job["evaluators"],
        "input": job["input"],
        "output": job["output"],
        "context": job["context"],
    }
    request = Request(
        JEV_API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {JEV_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jev returned HTTP {error.code}: {body[:1000]}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"Could not reach Jev: {error}") from error


def persist_results(job: dict[str, Any], response: dict[str, Any]) -> int:
    results = response.get("results", [])
    if not isinstance(results, list):
        raise ValueError("Jev response did not contain a results list")

    saved = 0
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            for result in results:
                metric_name = result.get("id")
                score = result.get("score")
                if not metric_name or not isinstance(score, (int, float)):
                    continue
                details = {
                    key: result[key]
                    for key in ("label", "kind", "family")
                    if key in result
                }
                cursor.execute(
                    """
                    INSERT INTO evaluations
                        (id, project_id, trace_id, metric_name, score, confidence,
                         evaluator_version, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (trace_id, metric_name, evaluator_version) DO UPDATE SET
                        score = EXCLUDED.score,
                        confidence = EXCLUDED.confidence,
                        details = EXCLUDED.details,
                        created_at = NOW()
                    """,
                    (
                        f"{job['trace_id']}:{metric_name}:{JEV_VERSION}",
                        job["project_id"],
                        job["trace_id"],
                        metric_name,
                        float(score),
                        result.get("confidence"),
                        JEV_VERSION,
                        json.dumps(details),
                    ),
                )
                saved += 1
    return saved


def process_job(job: dict[str, Any]) -> int:
    validate_job(job)
    return persist_results(job, call_jev(job))


def main() -> None:
    require_configuration()
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    print(f"Jev evaluator listening on {KAFKA_TOPIC}")
    for message in consumer:
        try:
            saved = process_job(message.value)
            consumer.commit()
            print(f"Evaluated trace {message.value['trace_id']}: saved {saved} scores")
        except ValueError as error:
            print(f"Dropping invalid evaluation job: {error}", file=sys.stderr)
            consumer.commit()
        except Exception as error:
            print(f"Evaluation failed; Kafka will retry the job: {error}", file=sys.stderr)
            time.sleep(2)


if __name__ == "__main__":
    main()
