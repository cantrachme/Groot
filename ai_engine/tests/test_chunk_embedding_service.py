import unittest
from unittest.mock import Mock

from ai_engine.app.embeddings import EmbeddingConfig, EmbeddingProvider
from ai_engine.app.services.chunk_embedding_service import (
    DocumentChunkEmbeddingService,
    DocumentChunkInput,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.1, 0.2, 0.3]


class DocumentChunkEmbeddingServiceTests(unittest.TestCase):
    def test_passes_chunk_ids_and_text_to_embedding_service(self):
        provider = FakeEmbeddingProvider()
        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )
        db = Mock()

        service = DocumentChunkEmbeddingService(
            provider=provider,
            config=config,
        )

        result = service.embed_chunks(
            db=db,
            chunks=[
                DocumentChunkInput(
                    document_chunk_id=10,
                    text="first chunk",
                ),
                DocumentChunkInput(
                    document_chunk_id=11,
                    text="second chunk",
                ),
            ],
        )

        self.assertEqual(
            provider.calls,
            [
                "first chunk",
                "second chunk",
            ],
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0].document_chunk_id,
            10,
        )
        self.assertEqual(
            result[1].document_chunk_id,
            11,
        )

    def test_empty_chunks_do_not_touch_database(self):
        provider = FakeEmbeddingProvider()
        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )
        db = Mock()

        service = DocumentChunkEmbeddingService(
            provider=provider,
            config=config,
        )

        result = service.embed_chunks(
            db=db,
            chunks=[],
        )

        self.assertEqual(result, [])
        provider_calls = provider.calls
        self.assertEqual(provider_calls, [])
        db.add.assert_not_called()
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
