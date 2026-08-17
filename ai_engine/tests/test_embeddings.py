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


class EmbeddingConfigTests(unittest.TestCase):
    def test_default_configuration(self):
        from ai_engine.app.embeddings import EmbeddingConfig

        config = EmbeddingConfig.from_env()

        self.assertEqual(config.provider, "local")
        self.assertEqual(config.model, "default")
        self.assertEqual(config.dimensions, 1536)
        self.assertEqual(config.batch_size, 32)

    def test_configuration_reads_environment(self):
        import os

        from ai_engine.app.embeddings import EmbeddingConfig

        previous = {
            key: os.environ.get(key)
            for key in (
                "EMBEDDING_PROVIDER",
                "EMBEDDING_MODEL",
                "EMBEDDING_DIMENSIONS",
                "EMBEDDING_BATCH_SIZE",
            )
        }

        try:
            os.environ["EMBEDDING_PROVIDER"] = "test"
            os.environ["EMBEDDING_MODEL"] = "model-a"
            os.environ["EMBEDDING_DIMENSIONS"] = "768"
            os.environ["EMBEDDING_BATCH_SIZE"] = "16"

            config = EmbeddingConfig.from_env()

            self.assertEqual(config.provider, "test")
            self.assertEqual(config.model, "model-a")
            self.assertEqual(config.dimensions, 768)
            self.assertEqual(config.batch_size, 16)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_invalid_dimensions_are_rejected(self):
        import os

        from ai_engine.app.embeddings import EmbeddingConfig

        previous = os.environ.get(
            "EMBEDDING_DIMENSIONS"
        )

        try:
            os.environ["EMBEDDING_DIMENSIONS"] = "0"

            with self.assertRaises(ValueError):
                EmbeddingConfig.from_env()
        finally:
            if previous is None:
                os.environ.pop("EMBEDDING_DIMENSIONS", None)
            else:
                os.environ["EMBEDDING_DIMENSIONS"] = previous
