from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..embeddings import EmbeddingConfig, EmbeddingProvider
from .embedding_service import EmbeddingService


@dataclass(frozen=True)
class DocumentChunkInput:
    document_chunk_id: int
    text: str


class DocumentChunkEmbeddingService:
    """Coordinates embedding generation for Django document chunks."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        config: EmbeddingConfig,
    ) -> None:
        self.embedding_service = EmbeddingService(
            provider=provider,
            config=config,
        )

    def embed_chunks(
        self,
        db: Session,
        chunks: list[DocumentChunkInput],
    ) -> list[object]:
        if not chunks:
            return []

        return self.embedding_service.embed_chunks(
            db=db,
            chunks=[
                (
                    chunk.document_chunk_id,
                    chunk.text,
                )
                for chunk in chunks
            ],
        )
