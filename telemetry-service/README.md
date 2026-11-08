# AITrace Telemetry Service

This folder contains the separate telemetry infrastructure. It is independent
from the RAG vector database in the project root.

## Start telemetry infrastructure

```bash
docker compose up -d
```

Services:

- Kafka: `localhost:9092`
- Telemetry PostgreSQL: `localhost:5433`

## Start the Java API

Java 21 and Maven are required for the backend.

```bash
cd backend
mvn spring-boot:run
```

The API listens on `http://localhost:8080`.

## Endpoint

```http
POST /api/v1/telemetry/batches
```

The endpoint validates a maximum of 20 events, publishes each event to the
`aitrace.telemetry.v1` Kafka topic, and returns `202 Accepted` only after Kafka
acknowledges all events.

Authentication is intentionally disabled for this first local milestone.

## Query stored telemetry

The Kafka consumer stores acknowledged events in telemetry PostgreSQL:

```bash
curl http://localhost:8080/api/v1/projects/local-project/traces
curl http://localhost:8080/api/v1/projects/local-project/metrics
curl http://localhost:8080/api/v1/traces/<trace-id>
```

## Jev evaluation worker

Apply the evaluation table migration to an existing telemetry database:

```bash
psql postgresql://telemetry:telemetry@localhost:5433/telemetry \
  -f db/migrations/002_evaluations.sql
```

Start the worker in another terminal. Use a newly rotated Jev key; never put
the key in source code or the React dashboard:

```bash
cd ../evaluation-service
python -m pip install -r requirements.txt
export JEV_API_KEY="your-rotated-key"
python evaluator_worker.py
```

Enable sampled semantic evaluation in the RAG process:

```bash
export AITRACE_CONTENT_SAMPLING=true
export AITRACE_SAMPLE_RATE=1.0  # use 0.05 after testing
export AITRACE_EVALUATION_URL=http://localhost:8080/api/v1/evaluation-jobs
```

The worker stores only Jev scores and metadata. Full question, context, and
answer content is sent only for explicitly sampled traces.

# Dashboard

The React dashboard lives in `../dashboard` and reads telemetry through the
Spring Boot Query API. It does not connect directly to Kafka or PostgreSQL.

Start the telemetry service first, then run:

```bash
cd dashboard
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`. The default project is `local-project`; change
`VITE_PROJECT_ID` in `.env` when querying another project.
