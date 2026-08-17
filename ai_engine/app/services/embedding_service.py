from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..embeddings import EmbeddingConfig, EmbeddingProvider
from ..models import DocumentChunkEmbedding


class EmbeddingService:
    """Generates and persists embeddings for document chunks."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        config: EmbeddingConfig,
    ) -> None:
        self.provider = provider
        self.config = config

    def embed_chunk(
        self,
        db: Session,
        document_chunk_id: int,
        text: str,
    ) -> DocumentChunkEmbedding:
        embedding = self.provider.embed_text(text)

        if len(embedding) != self.config.dimensions:
            raise ValueError(
                "Embedding dimensions do not match configuration: "
                f"expected {self.config.dimensions}, "
                f"got {len(embedding)}."
            )

        now = datetime.now(timezone.utc)

        record = DocumentChunkEmbedding(
            document_chunk_id=document_chunk_id,
            model=self.config.model,
            dimensions=self.config.dimensions,
            embedding=embedding,
            created_at=now,
            updated_at=now,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record
