from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Provider-independent interface for generating embeddings."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Embed multiple texts using the single-text contract by default.

        Providers with native batch embedding support may override this
        method to use a more efficient batch API.
        """
        return [
            self.embed_text(text)
            for text in texts
        ]
