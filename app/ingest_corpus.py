"""Embed the Virat Kohli corpus and store it in PostgreSQL + pgvector."""

from pathlib import Path

from aitrace_sdk import Trace

from app.vector_rag import LocalEmbeddingClient, PostgresVectorStore, chunk_pages, load_pages


def main() -> None:
    """Run the complete corpus ingestion workflow."""

    corpus_path = Path("data/virat_kohli/pages.jsonl")
    trace = Trace("virat-kohli-corpus-ingestion")

    try:
        with trace.span("load-corpus", "INGESTION") as span:
            pages = load_pages(corpus_path)
            span.set_metadata("page_count", len(pages))

        with trace.span("chunk-documents", "INGESTION") as span:
            chunks = chunk_pages(pages)
            span.set_metadata("chunk_count", len(chunks))

        with trace.span("create-embeddings", "EMBEDDING") as span:
            embedding_client = LocalEmbeddingClient()
            vectors = embedding_client.embed([chunk.text for chunk in chunks])
            span.set_metadata("model", embedding_client.model)
            span.set_metadata("embedding_count", len(vectors))
            span.set_metadata("dimensions", len(vectors[0]))

        with trace.span("store-embeddings", "DATABASE"):
            PostgresVectorStore().insert(pages, chunks, vectors)

        trace.finish()
        print(f"Ingested {len(pages)} pages and {len(chunks)} chunks.")
        print(trace.to_dict())
    except Exception as error:
        trace.fail(str(error))
        raise


if __name__ == "__main__":
    main()
