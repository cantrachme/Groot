import unittest
from unittest.mock import Mock

from ai_engine.app.models import DocumentChunkEmbedding
from ai_engine.app.services.similarity_search_service import (
    SimilaritySearchResult,
    SimilaritySearchService,
)


class SimilaritySearchServiceTests(unittest.TestCase):
    def test_returns_ranked_similarity_results(self):
        db = Mock()

        first = DocumentChunkEmbedding(
            id=1,
            document_chunk_id=10,
            model="test-model",
            dimensions=3,
            embedding=[0.1, 0.2, 0.3],
        )

        second = DocumentChunkEmbedding(
            id=2,
            document_chunk_id=11,
            model="test-model",
            dimensions=3,
            embedding=[0.4, 0.5, 0.6],
        )

        db.execute.return_value.all.return_value = [
            (first, 0.1),
            (second, 0.25),
        ]

        service = SimilaritySearchService()

        results = service.search(
            db=db,
            query_embedding=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
            top_k=2,
        )

        self.assertEqual(len(results), 2)

        self.assertIsInstance(
            results[0],
            SimilaritySearchResult,
        )

        self.assertIs(
            results[0].embedding,
            first,
        )
        self.assertAlmostEqual(
            results[0].distance,
            0.1,
        )
        self.assertAlmostEqual(
            results[0].similarity,
            0.9,
        )

        self.assertIs(
            results[1].embedding,
            second,
        )
        self.assertAlmostEqual(
            results[1].distance,
            0.25,
        )
        self.assertAlmostEqual(
            results[1].similarity,
            0.75,
        )

        db.execute.assert_called_once()

    def test_rejects_dimension_mismatch(self):
        db = Mock()

        service = SimilaritySearchService()

        with self.assertRaisesRegex(
            ValueError,
            "expected 3, got 2",
        ):
            service.search(
                db=db,
                query_embedding=[0.1, 0.2],
                model="test-model",
                dimensions=3,
                top_k=5,
            )

        db.execute.assert_not_called()

    def test_rejects_invalid_top_k(self):
        db = Mock()

        service = SimilaritySearchService()

        with self.assertRaisesRegex(
            ValueError,
            "top_k must be greater than zero",
        ):
            service.search(
                db=db,
                query_embedding=[0.1, 0.2, 0.3],
                model="test-model",
                dimensions=3,
                top_k=0,
            )

        db.execute.assert_not_called()

    def test_rejects_invalid_dimensions(self):
        db = Mock()

        service = SimilaritySearchService()

        with self.assertRaisesRegex(
            ValueError,
            "dimensions must be greater than zero",
        ):
            service.search(
                db=db,
                query_embedding=[],
                model="test-model",
                dimensions=0,
                top_k=5,
            )

        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
