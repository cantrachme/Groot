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

    def test_embeds_chunks_in_configured_batches(self):
        provider = Mock(spec=EmbeddingProvider)
        provider.embed_texts.side_effect = [
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ],
            [
                [0.7, 0.8, 0.9],
            ],
        ]

        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
            batch_size=2,
        )
        db = Mock()

        service = EmbeddingService(
            provider=provider,
            config=config,
        )

        result = service.embed_chunks(
            db=db,
            chunks=[
                (1, "first"),
                (2, "second"),
                (3, "third"),
            ],
        )

        self.assertEqual(len(result), 3)

        provider.embed_texts.assert_any_call(
            ["first", "second"],
        )
        provider.embed_texts.assert_any_call(
            ["third"],
        )

        self.assertEqual(
            provider.embed_texts.call_count,
            2,
        )

        db.add_all.assert_called_once_with(result)
        db.commit.assert_called_once_with()
        self.assertEqual(
            db.refresh.call_count,
            3,
        )

    def test_empty_batch_returns_without_database_work(self):
        provider = Mock(spec=EmbeddingProvider)
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

        result = service.embed_chunks(
            db=db,
            chunks=[],
        )

        self.assertEqual(result, [])
        provider.embed_texts.assert_not_called()
        db.add_all.assert_not_called()
        db.commit.assert_not_called()

    def test_rejects_unexpected_embedding_count(self):
        provider = Mock(spec=EmbeddingProvider)
        provider.embed_texts.return_value = [
            [0.1, 0.2, 0.3],
        ]

        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
            batch_size=2,
        )
        db = Mock()

        service = EmbeddingService(
            provider=provider,
            config=config,
        )

        with self.assertRaisesRegex(
            ValueError,
            "expected 2, got 1",
        ):
            service.embed_chunks(
                db=db,
                chunks=[
                    (1, "first"),
                    (2, "second"),
                ],
            )

        db.add_all.assert_not_called()
        db.commit.assert_not_called()

    def test_rejects_batch_dimension_mismatch(self):
        provider = Mock(spec=EmbeddingProvider)
        provider.embed_texts.return_value = [
            [0.1, 0.2],
            [0.3, 0.4],
        ]

        config = EmbeddingConfig(
            provider="fake",
            model="test-model",
            dimensions=3,
            batch_size=2,
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
            service.embed_chunks(
                db=db,
                chunks=[
                    (1, "first"),
                    (2, "second"),
                ],
            )

        db.add_all.assert_not_called()
        db.commit.assert_not_called()

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
