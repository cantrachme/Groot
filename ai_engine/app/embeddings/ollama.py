import json
import urllib.error
import urllib.request

from .config import EmbeddingConfig
from .provider import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Embedding provider backed by the local Ollama API."""

    def __init__(
        self,
        config: EmbeddingConfig,
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.config = config
        self.base_url = base_url.rstrip("/")

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("text must not be empty.")

        embeddings = self._embed([text])

        return embeddings[0]

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("texts must not contain empty text.")

        return self._embed(texts)

    def _embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        payload = json.dumps(
            {
                "model": self.config.model,
                "input": texts,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=60,
            ) as response:
                body = json.load(response)
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Unable to connect to Ollama embedding service."
            ) from exc

        embeddings = body.get("embeddings")

        if not isinstance(embeddings, list):
            raise RuntimeError(
                "Ollama embedding response did not contain embeddings."
            )

        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Ollama returned an unexpected number of embeddings: "
                f"expected {len(texts)}, got {len(embeddings)}."
            )

        for embedding in embeddings:
            if len(embedding) != self.config.dimensions:
                raise ValueError(
                    "Ollama embedding dimensions do not match configuration: "
                    f"expected {self.config.dimensions}, "
                    f"got {len(embedding)}."
                )

        return embeddings
