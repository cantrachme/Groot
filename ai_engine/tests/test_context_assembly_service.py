import unittest

from ai_engine.app.models import DocumentChunkEmbedding
from ai_engine.app.services.context_assembly_service import (
    AssembledContext,
    ContextAssemblyService,
)
from ai_engine.app.services.similarity_search_service import (
    SimilaritySearchResult,
)


def make_result(
    chunk_id: int,
    similarity: float,
) -> SimilaritySearchResult:
    embedding = DocumentChunkEmbedding(
        id=chunk_id,
        document_chunk_id=chunk_id,
        model="test-model",
        dimensions=3,
        embedding=[0.1, 0.2, 0.3],
    )

    return SimilaritySearchResult(
        embedding=embedding,
        distance=1.0 - similarity,
        similarity=similarity,
    )


class ContextAssemblyServiceTests(unittest.TestCase):
    def test_assembles_ranked_chunks(self):
        service = ContextAssemblyService()

        results = [
            make_result(42, 0.95),
            make_result(43, 0.80),
        ]

        context = service.assemble(
            results=results,
            chunk_texts={
                42: "First relevant chunk.",
                43: "Second relevant chunk.",
            },
        )

        self.assertIsInstance(
            context,
            AssembledContext,
        )

        self.assertEqual(
            [item.document_chunk_id for item in context.items],
            [42, 43],
        )

        self.assertIn(
            "[Chunk 42 | similarity=0.9500]",
            context.text,
        )
        self.assertIn(
            "First relevant chunk.",
            context.text,
        )
        self.assertIn(
            "Second relevant chunk.",
            context.text,
        )

    def test_skips_missing_chunks(self):
        service = ContextAssemblyService()

        context = service.assemble(
            results=[make_result(42, 0.95)],
            chunk_texts={},
        )

        self.assertEqual(context.items, ())
        self.assertEqual(context.text, "")

    def test_skips_empty_chunks(self):
        service = ContextAssemblyService()

        context = service.assemble(
            results=[
                make_result(42, 0.95),
                make_result(43, 0.90),
            ],
            chunk_texts={
                42: "   ",
                43: "Useful content.",
            },
        )

        self.assertEqual(
            [item.document_chunk_id for item in context.items],
            [43],
        )

    def test_respects_character_limit(self):
        service = ContextAssemblyService(
            max_characters=80,
        )

        context = service.assemble(
            results=[
                make_result(42, 0.95),
                make_result(43, 0.90),
            ],
            chunk_texts={
                42: "A" * 200,
                43: "B" * 200,
            },
        )

        self.assertLessEqual(
            len(context.text),
            80,
        )

        self.assertTrue(context.items)

    def test_rejects_invalid_character_limit(self):
        with self.assertRaisesRegex(
            ValueError,
            "max_characters must be greater than zero",
        ):
            ContextAssemblyService(
                max_characters=0,
            )


if __name__ == "__main__":
    unittest.main()
