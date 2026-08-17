import unittest

from ai_engine.app.embeddings import EmbeddingProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        return [
            float(len(text)),
        ]


class EmbeddingProviderTests(unittest.TestCase):
    def test_embedding_provider_contract(self):
        provider = FakeEmbeddingProvider()

        self.assertEqual(
            provider.embed_text("GROOT"),
            [5.0],
        )

    def test_embedding_provider_batch_default(self):
        provider = FakeEmbeddingProvider()

        self.assertEqual(
            provider.embed_texts(
                ["GROOT", "RAG"],
            ),
            [
                [5.0],
                [3.0],
            ],
        )


if __name__ == "__main__":
    unittest.main()
