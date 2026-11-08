"""A small Groq-powered RAG application instrumented with AITrace."""

import json
import os
import sys
from typing import Any

from aitrace_sdk import Trace


DOCUMENTS: list[dict[str, str]] = [
    {
        "id": "rag-intro",
        "text": "RAG combines document retrieval with language model generation.",
    },
    {
        "id": "retrieval",
        "text": "A retriever searches a document collection and selects relevant context.",
    },
    {
        "id": "tracing",
        "text": "A trace represents one request and spans represent operations inside it.",
    },
]


def _words(text: str) -> set[str]:
    """Return lowercase words from text for the first simple retriever."""

    return set(text.lower().replace(".", "").replace(",", "").split())


def retrieve(question: str, documents: list[dict[str, str]], top_k: int = 2) -> list[dict[str, str]]:
    """Return up to ``top_k`` documents sharing words with the question."""

    question_words = _words(question)
    scored_documents: list[tuple[int, dict[str, str]]] = []

    for document in documents:
        document_words = _words(document["text"])
        score = len(question_words & document_words)
        if score > 0:
            scored_documents.append((score, document))

    scored_documents.sort(key=lambda item: item[0], reverse=True)
    return [document for _, document in scored_documents[:top_k]]


def build_prompt(question: str, documents: list[dict[str, str]]) -> str:
    """Build a prompt that asks the model to answer from retrieved context."""

    context = "\n".join(
        f"[{document['id']}] {document['text']}" for document in documents
    )

    return (
        "Answer the question using only the context below. "
        "If the context does not contain the answer, say you do not know.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )


class GroqAnswerGenerator:
    """Generate an answer through Groq's Chat Completions API."""

    def __init__(self, model: str | None = None) -> None:
        try:
            from groq import Groq
        except ImportError as error:
            raise RuntimeError(
                "The Groq package is missing. Run: python3 -m pip install -r requirements.txt"
            ) from error

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Export it before running the RAG app.")

        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.client = Groq(api_key=api_key)
        self.last_usage: dict[str, Any] = {}

    def generate(self, prompt: str) -> str:
        """Send the prompt to Groq and return the model's text output."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        usage = getattr(response, "usage", None)
        if usage is not None:
            self.last_usage = {
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            }

        return response.choices[0].message.content or ""


def run_rag(
    question: str,
    documents: list[dict[str, str]] = DOCUMENTS,
    answer_generator: Any | None = None,
) -> tuple[str, Trace]:
    """Run retrieval and answer generation while recording a complete trace."""

    trace = Trace("question-answering")

    try:
        with trace.span("retrieve-documents", "RETRIEVAL") as retrieval_span:
            retrieved_documents = retrieve(question, documents)
            retrieval_span.set_metadata("top_k", 2)
            retrieval_span.set_metadata("document_count", len(retrieved_documents))
            retrieval_span.set_metadata(
                "document_ids", [document["id"] for document in retrieved_documents]
            )

        with trace.span("build-prompt", "PROMPT") as prompt_span:
            prompt = build_prompt(question, retrieved_documents)
            prompt_span.set_metadata("context_document_count", len(retrieved_documents))
            prompt_span.set_metadata("prompt_characters", len(prompt))

        with trace.span("generate-answer", "LLM") as llm_span:
            generator = answer_generator or GroqAnswerGenerator()
            answer = generator.generate(prompt)
            llm_span.set_metadata("model", getattr(generator, "model", "test-generator"))
            llm_span.metadata.update(getattr(generator, "last_usage", {}))

        trace.finish()
        return answer, trace
    except Exception as error:
        trace.fail(str(error))
        raise


def main() -> None:
    """Read a question from the command line and run the RAG application."""

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "What is retrieval augmented generation?"

    answer, trace = run_rag(question)
    print(f"Answer: {answer}\n")
    print("Trace:")
    print(json.dumps(trace.to_dict(), indent=2))


if __name__ == "__main__":
    main()
