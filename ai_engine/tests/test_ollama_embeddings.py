import json
import unittest
from unittest.mock import patch

from ai_engine.app.embeddings import (
    EmbeddingConfig,
    OllamaEmbeddingProvider,
)


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OllamaEmbeddingProviderTests(unittest.TestCase):
    def setUp(self):
        self.config = EmbeddingConfig(
            provider="ollama",
            model="nomic-embed-text:latest",
            dimensions=3,
            batch_size=2,
        )

    @patch("ai_engine.app.embeddings.ollama.urllib.request.urlopen")
    def test_embeds_single_text(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            {
                "model": "nomic-embed-text:latest",
                "embeddings": [
                    [0.1, 0.2, 0.3],
                ],
            }
        )

        provider = OllamaEmbeddingProvider(self.config)

        result = provider.embed_text("hello world")

        self.assertEqual(
            result,
            [0.1, 0.2, 0.3],
        )

        request = mock_urlopen.call_args.args[0]

        self.assertEqual(
            request.full_url,
            "http://localhost:11434/api/embed",
        )

        payload = json.loads(request.data.decode("utf-8"))

        self.assertEqual(
            payload["model"],
            "nomic-embed-text:latest",
        )
        self.assertEqual(
            payload["input"],
            ["hello world"],
        )

    @patch("ai_engine.app.embeddings.ollama.urllib.request.urlopen")
    def test_embeds_multiple_texts(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            {
                "model": "nomic-embed-text:latest",
                "embeddings": [
                    [0.1, 0.2, 0.3],
                    [0.4, 0.5, 0.6],
                ],
            }
        )

        provider = OllamaEmbeddingProvider(self.config)

        result = provider.embed_texts(
            ["hello", "world"],
        )

        self.assertEqual(
            result,
            [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
            ],
        )

    def test_rejects_empty_text(self):
        provider = OllamaEmbeddingProvider(self.config)

        with self.assertRaisesRegex(
            ValueError,
            "text must not be empty",
        ):
            provider.embed_text("")

    def test_rejects_empty_text_in_batch(self):
        provider = OllamaEmbeddingProvider(self.config)

        with self.assertRaisesRegex(
            ValueError,
            "texts must not contain empty text",
        ):
            provider.embed_texts(
                ["hello", "  "],
            )

    def test_empty_batch_returns_empty(self):
        provider = OllamaEmbeddingProvider(self.config)

        self.assertEqual(
            provider.embed_texts([]),
            [],
        )

    @patch("ai_engine.app.embeddings.ollama.urllib.request.urlopen")
    def test_rejects_dimension_mismatch(self, mock_urlopen):
        mock_urlopen.return_value = FakeHTTPResponse(
            {
                "model": "nomic-embed-text:latest",
                "embeddings": [
                    [0.1, 0.2],
                ],
            }
        )

        provider = OllamaEmbeddingProvider(self.config)

        with self.assertRaisesRegex(
            ValueError,
            "expected 3, got 2",
        ):
            provider.embed_text("hello")


if __name__ == "__main__":
    unittest.main()
