"""FastAPI service for uploading PDFs, asking questions, and evaluating answers."""

import io
import json
import os
import time
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pypdf import PdfReader

from aitrace_sdk import HttpExporter, Trace
from app.vector_rag import EMBEDDING_DIMENSIONS, LocalEmbeddingClient, vector_literal


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aitrace:aitrace@localhost:5432/aitrace")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
JEV_API_KEY = os.getenv("JEV_API_KEY")
JEV_API_URL = os.getenv("JEV_API_URL", "https://jeval.dev/api/v1/evaluate")
TELEMETRY_URL = os.getenv("AITRACE_INGESTION_URL")
MAX_FILE_BYTES = int(os.getenv("MAX_PDF_BYTES", str(10 * 1024 * 1024)))


class ChatRequest(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=10)


class EvaluateRequest(BaseModel):
    workspace_id: str = Field(min_length=1, max_length=120)


app = FastAPI(title="AITrace PDF RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("DASHBOARD_ORIGIN", "*").split(","),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def embedding_client() -> LocalEmbeddingClient:
    return LocalEmbeddingClient()


def ensure_schema() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES rag_documents(id) ON DELETE CASCADE,
                    workspace_id TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector(384) NOT NULL,
                    UNIQUE(document_id, chunk_index)
                );
                CREATE INDEX IF NOT EXISTS rag_chunks_workspace_idx ON rag_chunks(workspace_id);
                CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
                    ON rag_chunks USING hnsw (embedding vector_cosine_ops);
                CREATE TABLE IF NOT EXISTS rag_runs (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    context JSONB NOT NULL,
                    sources JSONB NOT NULL,
                    duration_ms DOUBLE PRECISION NOT NULL,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS rag_evaluations (
                    id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    score DOUBLE PRECISION NOT NULL,
                    confidence DOUBLE PRECISION,
                    details JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(trace_id, metric_name)
                );
                """
            )


@app.on_event("startup")
def startup() -> None:
    ensure_schema()


def split_text(text: str, words_per_chunk: int = 180, overlap: int = 30) -> list[str]:
    words = text.split()
    step = words_per_chunk - overlap
    return [" ".join(words[start : start + words_per_chunk]) for start in range(0, len(words), step) if words[start : start + words_per_chunk]]


def extract_pdf(content: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(io.BytesIO(content))
    pages: list[tuple[int, str]] = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((number, text))
    return pages


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/documents/upload")
async def upload_documents(
    workspace_id: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    if not workspace_id.strip() or len(workspace_id) > 120:
        raise HTTPException(400, "workspace_id is required")
    if not files:
        raise HTTPException(400, "at least one PDF is required")

    inserted: list[dict[str, Any]] = []
    for upload in files:
        content = await upload.read()
        if len(content) > MAX_FILE_BYTES:
            raise HTTPException(413, f"{upload.filename} is larger than the upload limit")
        if upload.content_type not in {"application/pdf", "application/octet-stream"} and not (upload.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"{upload.filename} is not a PDF")

        pages = extract_pdf(content)
        chunks = [(page_number, index, chunk) for page_number, text in pages for index, chunk in enumerate(split_text(text))]
        if not chunks:
            raise HTTPException(400, f"{upload.filename} did not contain extractable text")

        vectors = embedding_client().embed([item[2] for item in chunks])
        document_id = str(uuid4())
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO rag_documents (id, workspace_id, filename, page_count, chunk_count) VALUES (%s, %s, %s, %s, %s)",
                    (document_id, workspace_id, upload.filename or "document.pdf", len(pages), len(chunks)),
                )
                for (page_number, index, text), vector in zip(chunks, vectors):
                    cursor.execute(
                        "INSERT INTO rag_chunks (id, document_id, workspace_id, page_number, chunk_index, text, embedding) VALUES (%s, %s, %s, %s, %s, %s, %s::vector)",
                        (str(uuid4()), document_id, workspace_id, page_number, index, text, vector_literal(vector)),
                    )
        inserted.append({"id": document_id, "filename": upload.filename, "page_count": len(pages), "chunk_count": len(chunks)})

    return {"documents": inserted}


def search_chunks(workspace_id: str, vector: list[float], top_k: int) -> list[dict[str, Any]]:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.id, c.text, c.page_number, d.filename,
                       1 - (c.embedding <=> %s::vector) AS similarity
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.document_id
                WHERE c.workspace_id = %s
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
                """,
                (vector_literal(vector), workspace_id, vector_literal(vector), top_k),
            )
            columns = [description.name for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def export_trace(trace: Trace, workspace_id: str) -> None:
    if not TELEMETRY_URL:
        return
    exporter = HttpExporter(TELEMETRY_URL, workspace_id)
    exporter.export_trace(trace)
    exporter.shutdown()


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(500, "GROQ_API_KEY is not configured on the server")
    trace = Trace("pdf-rag-question-answering")
    started = time.perf_counter()
    try:
        from groq import Groq

        with trace.span("embed-query", "EMBEDDING") as span:
            query_vector = embedding_client().embed([request.question])[0]
            span.set_metadata("model", embedding_client().model)
        with trace.span("vector-search", "RETRIEVAL") as span:
            results = search_chunks(request.workspace_id, query_vector, request.top_k)
            span.set_metadata("top_k", request.top_k)
            span.set_metadata("result_count", len(results))
        if not results:
            raise HTTPException(404, "Upload a PDF before asking a question")

        context = "\n\n".join(f"[{item['filename']} — page {item['page_number']}] {item['text']}" for item in results)
        prompt = "Answer only from the supplied PDF context. If the context is insufficient, say you do not know.\n\nContext:\n" + context + "\n\nQuestion: " + request.question
        with trace.span("generate-answer", "LLM") as span:
            response = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            usage = getattr(response, "usage", None)
            if usage:
                span.set_metadata("prompt_tokens", getattr(usage, "prompt_tokens", None))
                span.set_metadata("completion_tokens", getattr(usage, "completion_tokens", None))
            answer = response.choices[0].message.content or ""

        trace.finish()
        sources = [{"filename": item["filename"], "page_number": item["page_number"], "similarity": round(float(item["similarity"]), 4)} for item in results]
        usage = getattr(response, "usage", None)
        with psycopg.connect(DATABASE_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO rag_runs (id, workspace_id, question, answer, context, sources, duration_ms, input_tokens, output_tokens) VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)",
                    (trace.id, request.workspace_id, request.question, answer, json.dumps([item["text"] for item in results]), json.dumps(sources), trace.duration_ms or (time.perf_counter() - started) * 1000, getattr(usage, "prompt_tokens", None) if usage else None, getattr(usage, "completion_tokens", None) if usage else None),
                )
        export_trace(trace, request.workspace_id)
        return {"trace_id": trace.id, "answer": answer, "sources": sources, "analytics": {"duration_ms": trace.duration_ms, "input_tokens": getattr(usage, "prompt_tokens", None) if usage else None, "output_tokens": getattr(usage, "completion_tokens", None) if usage else None}}
    except HTTPException:
        raise
    except Exception as error:
        trace.fail(str(error))
        raise HTTPException(500, str(error)) from error


@app.post("/api/evaluations/{trace_id}")
def evaluate(trace_id: str, request: EvaluateRequest) -> dict[str, Any]:
    if not JEV_API_KEY:
        raise HTTPException(500, "JEV_API_KEY is not configured on the server")
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT question, answer, context FROM rag_runs WHERE id = %s AND workspace_id = %s", (trace_id, request.workspace_id))
            row = cursor.fetchone()
    if not row:
        raise HTTPException(404, "RAG run not found")

    body = json.dumps({"evaluators": ["faithfulness", "answer_relevancy", "context_precision"], "input": row[0], "output": row[1], "context": row[2]}).encode()
    try:
        with urlopen(Request(JEV_API_URL, data=body, headers={"Authorization": f"Bearer {JEV_API_KEY}", "Content-Type": "application/json"}, method="POST"), timeout=30) as response:
            result = json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError) as error:
        raise HTTPException(502, f"Jev evaluation failed: {error}") from error

    saved: list[dict[str, Any]] = []
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            for item in result.get("results", []):
                if item.get("id") is None or not isinstance(item.get("score"), (int, float)):
                    continue
                details = {key: item[key] for key in ("label", "family", "kind") if key in item}
                cursor.execute(
                    "INSERT INTO rag_evaluations (id, trace_id, workspace_id, metric_name, score, confidence, details) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb) ON CONFLICT (trace_id, metric_name) DO UPDATE SET score = EXCLUDED.score, confidence = EXCLUDED.confidence, details = EXCLUDED.details",
                    (f"{trace_id}:{item['id']}", trace_id, request.workspace_id, item["id"], float(item["score"]), item.get("confidence"), json.dumps(details)),
                )
                saved.append({"metric_name": item["id"], "score": item["score"], "confidence": item.get("confidence")})
    return {"trace_id": trace_id, "evaluations": saved}
