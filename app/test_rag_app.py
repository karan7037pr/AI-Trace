import unittest

from app.rag_app import build_prompt, retrieve, run_rag


class FakeAnswerGenerator:
    model = "fake-model"
    last_usage = {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}

    def generate(self, prompt: str) -> str:
        self.prompt = prompt
        return "RAG retrieves context before generating an answer."


class RagAppTests(unittest.TestCase):
    def test_retrieve_returns_matching_documents(self):
        documents = [
            {"id": "one", "text": "Cats are animals."},
            {"id": "two", "text": "RAG retrieves documents."},
        ]

        result = retrieve("How does RAG retrieve documents?", documents, top_k=1)

        self.assertEqual(["two"], [document["id"] for document in result])

    def test_build_prompt_contains_question_and_context(self):
        prompt = build_prompt(
            "What is RAG?",
            [{"id": "doc-1", "text": "RAG uses retrieved context."}],
        )

        self.assertIn("What is RAG?", prompt)
        self.assertIn("RAG uses retrieved context.", prompt)

    def test_run_rag_records_spans_without_api_call(self):
        answer, trace = run_rag(
            "What is RAG?",
            documents=[{"id": "doc-1", "text": "RAG uses retrieved context."}],
            answer_generator=FakeAnswerGenerator(),
        )

        self.assertIn("RAG", answer)
        self.assertEqual("OK", trace.status)
        self.assertEqual(
            ["RETRIEVAL", "PROMPT", "LLM"],
            [span.span_type for span in trace.spans],
        )
        self.assertEqual(15, trace.spans[-1].metadata["total_tokens"])


if __name__ == "__main__":
    unittest.main()
