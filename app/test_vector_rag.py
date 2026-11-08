import unittest

from app.vector_rag import EMBEDDING_DIMENSIONS, Page, chunk_page, vector_literal


class VectorRagTests(unittest.TestCase):
    def test_chunk_page_creates_overlapping_chunks(self):
        page = Page(
            id="page-1",
            title="Test page",
            page_number=1,
            text="one two three four five six seven eight nine ten",
            source_url="https://example.com",
            source_title="Example",
            retrieved_at="2026-01-01",
        )

        chunks = chunk_page(page, words_per_chunk=5, overlap=2)

        self.assertEqual("one two three four five", chunks[0].text)
        self.assertEqual("four five six seven eight", chunks[1].text)
        self.assertEqual(page.id, chunks[0].page.id)

    def test_vector_literal_has_pgvector_shape(self):
        self.assertEqual("[0.1,-0.2,3.0]", vector_literal([0.1, -0.2, 3.0]))

    def test_local_embedding_dimension_matches_database_schema(self):
        self.assertEqual(384, EMBEDDING_DIMENSIONS)


if __name__ == "__main__":
    unittest.main()
