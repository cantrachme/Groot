import unittest
from unittest.mock import Mock

from ai_engine.app.embeddings import EmbeddingConfig, EmbeddingProvider
from ai_engine.app.models import DocumentChunkEmbedding
from ai_engine.app.services.retrieval_service import (
    RetrievalResult,
    RetrievalService,
)
from ai_engine.app.services.similarity_search_service import (
    SimilaritySearchResult,
    SimilaritySearchService,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.1, 0.2, 0.3]


class RetrievalServiceTests(unittest.TestCase):
    def test_embeds_query_and_retrieves_results(self):
        provider = FakeEmbeddingProvider()
        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )

        similarity_search = Mock(
            spec=SimilaritySearchService,
        )

        embedding = DocumentChunkEmbedding(
            id=1,
            document_chunk_id=42,
            model="test-model",
            dimensions=3,
            embedding=[0.1, 0.2, 0.3],
        )

        similarity_search.search.return_value = [
            SimilaritySearchResult(
                embedding=embedding,
                distance=0.1,
                similarity=0.9,
            ),
        ]

        db = Mock()

        service = RetrievalService(
            provider=provider,
            config=config,
            similarity_search=similarity_search,
        )

        result = service.retrieve(
            db=db,
            query="What is this document?",
            top_k=3,
        )

        self.assertIsInstance(
            result,
            RetrievalResult,
        )

        self.assertEqual(
            result.query,
            "What is this document?",
        )

        self.assertEqual(
            len(result.results),
            1,
        )

        self.assertIs(
            result.results[0].embedding,
            embedding,
        )

        self.assertEqual(
            provider.calls,
            ["What is this document?"],
        )

        similarity_search.search.assert_called_once_with(
            db=db,
            query_embedding=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
            top_k=3,
        )

    def test_uses_default_top_k(self):
        provider = FakeEmbeddingProvider()
        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )

        similarity_search = Mock(
            spec=SimilaritySearchService,
        )
        similarity_search.search.return_value = []

        service = RetrievalService(
            provider=provider,
            config=config,
            similarity_search=similarity_search,
        )

        service.retrieve(
            db=Mock(),
            query="hello",
        )

        similarity_search.search.assert_called_once_with(
            db=similarity_search.search.call_args.kwargs["db"],
            query_embedding=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
            top_k=5,
        )

    def test_rejects_empty_query(self):
        provider = Mock(spec=EmbeddingProvider)
        similarity_search = Mock(
            spec=SimilaritySearchService,
        )

        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )

        service = RetrievalService(
            provider=provider,
            config=config,
            similarity_search=similarity_search,
        )

        with self.assertRaisesRegex(
            ValueError,
            "query must not be empty",
        ):
            service.retrieve(
                db=Mock(),
                query="   ",
            )

        provider.embed_text.assert_not_called()
        similarity_search.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
