import unittest
from unittest.mock import Mock

from ai_engine.app.embeddings import EmbeddingConfig, EmbeddingProvider
from ai_engine.app.services.embedding_service import EmbeddingService


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.calls: list[str] = []

    def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return self.embedding


class EmbeddingServiceTests(unittest.TestCase):
    def test_generates_and_persists_embedding(self):
        provider = FakeEmbeddingProvider(
            [0.1, 0.2, 0.3],
        )
        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )
        db = Mock()

        service = EmbeddingService(
            provider=provider,
            config=config,
        )

        result = service.embed_chunk(
            db=db,
            document_chunk_id=42,
            text="hello world",
        )

        self.assertEqual(
            provider.calls,
            ["hello world"],
        )
        self.assertEqual(
            result.document_chunk_id,
            42,
        )
        self.assertEqual(
            result.model,
            "test-model",
        )
        self.assertEqual(
            result.dimensions,
            3,
        )
        self.assertEqual(
            result.embedding,
            [0.1, 0.2, 0.3],
        )

        db.add.assert_called_once_with(result)
        db.commit.assert_called_once_with()
        db.refresh.assert_called_once_with(result)

    def test_rejects_dimension_mismatch(self):
        provider = FakeEmbeddingProvider(
            [0.1, 0.2],
        )
        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
        )
        db = Mock()

        service = EmbeddingService(
            provider=provider,
            config=config,
        )

        with self.assertRaisesRegex(
            ValueError,
            "expected 3, got 2",
        ):
            service.embed_chunk(
                db=db,
                document_chunk_id=42,
                text="hello world",
            )

        db.add.assert_not_called()
        db.commit.assert_not_called()

    def test_uses_configured_model_and_dimensions(self):
        provider = FakeEmbeddingProvider(
            [0.1, 0.2, 0.3, 0.4],
        )
        config = EmbeddingConfig(
            provider="fake",
            model="custom-model",
            dimensions=4,
        )
        db = Mock()

        service = EmbeddingService(
            provider=provider,
            config=config,
        )

        result = service.embed_chunk(
            db=db,
            document_chunk_id=99,
            text="document text",
        )

        self.assertEqual(
            result.model,
            "custom-model",
        )
        self.assertEqual(
            result.dimensions,
            4,
        )


if __name__ == "__main__":
    unittest.main()
