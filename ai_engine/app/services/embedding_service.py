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

    def embed_chunks(
        self,
        db: Session,
        chunks: list[tuple[int, str]],
    ) -> list[DocumentChunkEmbedding]:
        if not chunks:
            return []

        records: list[DocumentChunkEmbedding] = []

        for start in range(0, len(chunks), self.config.batch_size):
            batch = chunks[
                start:start + self.config.batch_size
            ]

            embeddings = self.provider.embed_texts(
                [text for _, text in batch],
            )

            if len(embeddings) != len(batch):
                raise ValueError(
                    "Embedding provider returned an unexpected "
                    "number of embeddings: "
                    f"expected {len(batch)}, "
                    f"got {len(embeddings)}."
                )

            now = datetime.now(timezone.utc)

            for (document_chunk_id, _), embedding in zip(
                batch,
                embeddings,
            ):
                if len(embedding) != self.config.dimensions:
                    raise ValueError(
                        "Embedding dimensions do not match "
                        "configuration: "
                        f"expected {self.config.dimensions}, "
                        f"got {len(embedding)}."
                    )

                records.append(
                    DocumentChunkEmbedding(
                        document_chunk_id=document_chunk_id,
                        model=self.config.model,
                        dimensions=self.config.dimensions,
                        embedding=embedding,
                        created_at=now,
                        updated_at=now,
                    )
                )

        db.add_all(records)
        db.commit()

        for record in records:
            db.refresh(record)

        return records
