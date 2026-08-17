from dataclasses import dataclass
import os


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimensions: int
    batch_size: int = 32

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        provider = os.getenv(
            "EMBEDDING_PROVIDER",
            "local",
        )
        model = os.getenv(
            "EMBEDDING_MODEL",
            "default",
        )
        dimensions = int(
            os.getenv(
                "EMBEDDING_DIMENSIONS",
                "1536",
            )
        )
        batch_size = int(
            os.getenv(
                "EMBEDDING_BATCH_SIZE",
                "32",
            )
        )

        if dimensions <= 0:
            raise ValueError(
                "EMBEDDING_DIMENSIONS must be greater than zero."
            )

        if batch_size <= 0:
            raise ValueError(
                "EMBEDDING_BATCH_SIZE must be greater than zero."
            )

        return cls(
            provider=provider,
            model=model,
            dimensions=dimensions,
            batch_size=batch_size,
        )
