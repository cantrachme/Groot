import hashlib
import math

from .config import EmbeddingConfig
from .provider import EmbeddingProvider


class LocalEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embedding provider for development."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config

    def embed_text(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("text must not be empty.")

        values: list[float] = []

        for index in range(self.config.dimensions):
            digest = hashlib.sha256(
                f"{index}:{text}".encode("utf-8")
            ).digest()

            value = int.from_bytes(
                digest[:8],
                byteorder="big",
                signed=False,
            )

            normalized = (
                (value / ((1 << 64) - 1)) * 2.0
            ) - 1.0

            values.append(normalized)

        norm = math.sqrt(
            sum(value * value for value in values)
        )

        if norm == 0:
            return [0.0] * self.config.dimensions

        return [
            value / norm
            for value in values
        ]
