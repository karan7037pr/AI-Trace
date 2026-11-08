"""Reusable pieces for the PostgreSQL + pgvector RAG pipeline."""

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from aitrace_sdk import Trace


EMBEDDING_MODEL = os.getenv(
    "LOCAL_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)
EMBEDDING_DIMENSIONS = 384
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aitrace:aitrace@localhost:5432/aitrace",
)


@dataclass(frozen=True)
class Page:
    """One source page in the learning corpus."""

    id: str
    title: str
    page_number: int
    text: str
    source_url: str
    source_title: str
    retrieved_at: str


@dataclass(frozen=True)
class Chunk:
    """A smaller searchable piece of a page."""

    id: str
    page: Page
    chunk_index: int
    text: str


def load_pages(path: str | Path) -> list[Page]:
    """Read one JSON object per line and convert each object to a Page."""

    pages: list[Page] = []
    with Path(path).open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                pages.append(Page(**json.loads(line)))

    if len(pages) != 20:
        raise ValueError(f"Expected 20 pages, found {len(pages)}")

    return pages


def chunk_page(page: Page, words_per_chunk: int = 120, overlap: int = 20) -> list[Chunk]:
    """Split a page into overlapping word windows for retrieval."""

    words = page.text.split()
    if overlap >= words_per_chunk:
        raise ValueError("overlap must be smaller than words_per_chunk")

    chunks: list[Chunk] = []
    start = 0
    chunk_index = 0
    step = words_per_chunk - overlap

    while start < len(words):
        text = " ".join(words[start : start + words_per_chunk])
        chunks.append(Chunk(str(uuid4()), page, chunk_index, text))
        start += step
        chunk_index += 1

    return chunks


def chunk_pages(pages: list[Page]) -> list[Chunk]:
    """Chunk every page using the default chunking settings."""

    chunks: list[Chunk] = []
    for page in pages:
        chunks.extend(chunk_page(page))
    return chunks


class LocalEmbeddingClient:
    """Create vectors locally with a Sentence Transformers model."""

    def __init__(self, model: str = EMBEDDING_MODEL) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise RuntimeError(
                "Install dependencies with: pip install -r requirements.txt"
            ) from error

        self.model = model
        self.client = SentenceTransformer(self.model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector for every input string."""

        matrix = self.client.encode(
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        vectors = [row.tolist() for row in matrix]
        if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
            raise ValueError("The embedding dimension does not match the database schema")
        return vectors


def vector_literal(vector: list[float]) -> str:
    """Convert a Python list into pgvector's text representation."""

    return "[" + ",".join(str(value) for value in vector) + "]"


class PostgresVectorStore:
    """Persist pages and chunks, then search chunks by cosine distance."""

    def __init__(self, database_url: str = DATABASE_URL) -> None:
        try:
            import psycopg
        except ImportError as error:
            raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from error

        self.psycopg = psycopg
        self.database_url = database_url

    def insert(self, pages: list[Page], chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Insert pages and chunks idempotently."""

        if len(chunks) != len(vectors):
            raise ValueError("Every chunk must have exactly one embedding")

        with self.psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                for page in pages:
                    cursor.execute(
                        """
                        INSERT INTO documents
                            (id, title, page_number, text, source_url, source_title, retrieved_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            page_number = EXCLUDED.page_number,
                            text = EXCLUDED.text,
                            source_url = EXCLUDED.source_url,
                            source_title = EXCLUDED.source_title,
                            retrieved_at = EXCLUDED.retrieved_at
                        """,
                        (page.id, page.title, page.page_number, page.text, page.source_url,
                         page.source_title, page.retrieved_at),
                    )

                for chunk, vector in zip(chunks, vectors):
                    cursor.execute(
                        """
                        INSERT INTO document_chunks (id, document_id, chunk_index, text, embedding)
                        VALUES (%s, %s, %s, %s, %s::vector)
                        ON CONFLICT (document_id, chunk_index) DO UPDATE SET
                            text = EXCLUDED.text,
                            embedding = EXCLUDED.embedding
                        """,
                        (chunk.id, chunk.page.id, chunk.chunk_index, chunk.text, vector_literal(vector)),
                    )

    def search(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        """Return the closest chunks and their cosine similarity scores."""

        with self.psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT c.id, c.document_id, c.chunk_index, c.text,
                           d.title, d.page_number, d.source_url, d.source_title,
                           1 - (c.embedding <=> %s::vector) AS similarity
                    FROM document_chunks c
                    JOIN documents d ON d.id = c.document_id
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector_literal(vector), vector_literal(vector), top_k),
                )
                columns = [description.name for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]


def build_context(results: list[dict[str, Any]]) -> str:
    """Format retrieved chunks for the answer-generation prompt."""

    return "\n\n".join(
        f"[{result['source_title']} — page {result['page_number']}] {result['text']}"
        for result in results
    )


def should_sample_for_evaluation() -> bool:
    """Return whether this trace may send full content to the evaluator."""

    enabled = os.getenv("AITRACE_CONTENT_SAMPLING", "false").lower() == "true"
    if not enabled:
        return False
    rate = float(os.getenv("AITRACE_SAMPLE_RATE", "0.05"))
    return random.random() < max(0.0, min(rate, 1.0))


def ask_vector_rag(question: str, store: PostgresVectorStore, top_k: int = 5) -> tuple[str, Trace]:
    """Embed a question, search PostgreSQL, and answer from retrieved context."""

    try:
        from groq import Groq
    except ImportError as error:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from error

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Export it before asking a question.")

    trace = Trace("virat-kohli-question-answering")
    client = Groq(api_key=api_key)
    embedding_client = LocalEmbeddingClient()
    answer_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    try:
        with trace.span("embed-query", "EMBEDDING") as span:
            query_vector = embedding_client.embed([question])[0]
            span.set_metadata("model", EMBEDDING_MODEL)
            span.set_metadata("dimensions", EMBEDDING_DIMENSIONS)

        with trace.span("vector-search", "RETRIEVAL") as span:
            results = store.search(query_vector, top_k)
            span.set_metadata("top_k", top_k)
            span.set_metadata("result_count", len(results))
            span.set_metadata("similarities", [round(float(r["similarity"]), 4) for r in results])

        with trace.span("build-prompt", "PROMPT") as span:
            context = build_context(results)
            prompt = (
                "Answer the question using only the supplied context. "
                "If the context is insufficient, say you do not know.\n\n"
                f"Context:\n{context}\n\nQuestion: {question}"
            )
            span.set_metadata("context_chunks", len(results))
            span.set_metadata("prompt_characters", len(prompt))

        with trace.span("generate-answer", "LLM") as span:
            response = client.chat.completions.create(
                model=answer_model,
                messages=[{"role": "user", "content": prompt}],
            )
            span.set_metadata("provider", "groq")
            span.set_metadata("model", answer_model)
            usage = getattr(response, "usage", None)
            if usage:
                span.set_metadata("prompt_tokens", getattr(usage, "prompt_tokens", None))
                span.set_metadata("completion_tokens", getattr(usage, "completion_tokens", None))
                span.set_metadata("total_tokens", getattr(usage, "total_tokens", None))

        if should_sample_for_evaluation():
            trace.evaluation_payload = {
                "input": question,
                "output": response.choices[0].message.content or "",
                "context": [result["text"] for result in results],
                "evaluators": ["faithfulness", "answer_relevancy", "context_precision"],
            }

        trace.finish()
        return response.choices[0].message.content or "", trace
    except Exception as error:
        trace.fail(str(error))
        raise
