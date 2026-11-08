# AITrace

AITrace is a learning project for building a RAG observability platform one small
piece at a time.

## Learning roadmap

1. Build a local tracer in Python.
2. Add an asynchronous batch processor and HTTP exporter.
3. Build a small Spring Boot ingestion API.
4. Add PostgreSQL persistence.
5. Add Kafka buffering and idempotent consumers.
6. Add retrieval metrics and sampled semantic evaluation.
7. Build the React dashboard.
8. Load-test the complete ingestion path.

The first milestone is intentionally local: it demonstrates the core tracing
model without requiring any external service.

## Run milestone 1

```bash
PYTHONPATH=sdk:. python3 sdk/example.py
```

The example creates one trace with nested retrieval and generation spans, then
prints the structured telemetry that a later exporter can send to the backend.

## Run the Groq RAG example

Install the Python dependency:

```bash
python3 -m pip install -r requirements.txt
```

Set your Groq API key in the shell. Do not paste it into source code:

```bash
export GROQ_API_KEY="your-groq-api-key"
export GROQ_MODEL="openai/gpt-oss-20b"
```

Then ask a question:

```bash
PYTHONPATH=sdk:. python3 app/rag_app.py "What is retrieval augmented generation?"
```

The application retrieves local documents, sends the question and retrieved
context to Groq, and prints both the answer and the AITrace data.

## Build the real vector RAG application

Start PostgreSQL with the pgvector extension:

```bash
docker compose up -d
```

Generate the 20-page, source-backed Virat Kohli corpus:

```bash
PYTHONPATH=sdk:. python3 -m app.generate_corpus
```

Create embeddings and store them in PostgreSQL:

```bash
PYTHONPATH=sdk:. python3 -m app.ingest_corpus
```

Ask a question using vector similarity search:

```bash
PYTHONPATH=sdk:. python3 -m app.ask "What were Virat Kohli's major Test career milestones?"
```

The corpus generator uses source-backed topic briefs and stores source URLs and
retrieval dates with every page. Groq generates the page text and final answers
within its account limits. Embeddings are generated locally with the
open-source `sentence-transformers/all-MiniLM-L6-v2` model. The vector database
stores 384-dimensional vectors. The first run downloads the model; later runs
use the local model cache.

## Public PDF RAG demo

The resume-ready demo is a FastAPI service plus the React dashboard. It accepts
PDFs, extracts and chunks their text, stores local embeddings in PostgreSQL with
pgvector, answers questions with Groq, and evaluates an answer with Jev.

Run the API locally from the repository root:

```bash
export DATABASE_URL=postgresql://aitrace:aitrace@localhost:5432/aitrace
export GROQ_API_KEY="your-groq-key"
export JEV_API_KEY="your-jev-key"
.venv/bin/uvicorn rag_api.main:app --reload --port 8000
```

Set the dashboard API URL in `dashboard/.env`:

```bash
VITE_RAG_API_BASE_URL=http://localhost:8000
```

Then run:

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173`. The main page is the PDF RAG demo; the existing
observability dashboard is available at `/observability`.

### Free deployment shape

1. Create a Neon PostgreSQL database and run `CREATE EXTENSION vector` once.
2. In Render, create a web service from this repository using the included
   `render.yaml` Blueprint. It builds `rag-api/Dockerfile` and exposes
   `/api/health` as its health check.
3. Add these Render environment values: `DATABASE_URL`, `GROQ_API_KEY`,
   `JEV_API_KEY`, and `DASHBOARD_ORIGIN`. `GROQ_MODEL` and `JEV_API_URL`
   already have safe defaults in the Blueprint.
4. In Vercel, import this repository with `dashboard` as the root directory.
   Use `npm run build` as the build command and `dist` as the output directory.
   Set `VITE_RAG_API_BASE_URL` to the deployed Render URL.
5. Copy the Vercel URL into Render's `DASHBOARD_ORIGIN`, then redeploy the
   Render service.

Render's free web service can sleep when idle, so the first request after a
quiet period may be slow. The free demo is intentionally not an authenticated
multi-user production service.

The public demo intentionally has no login system. A browser-generated workspace
ID keeps documents from different demo sessions separate at the application
level; it is not a security boundary.
