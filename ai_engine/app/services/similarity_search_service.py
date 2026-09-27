from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import DocumentChunkEmbedding
from .tenant_scope import tenant_options


@dataclass(frozen=True)
class SimilaritySearchResult:
    embedding: DocumentChunkEmbedding
    distance: float
    similarity: float


class SimilaritySearchService:
    """Retrieves document chunk embeddings by cosine similarity."""

    def search(
        self,
        db: Session,
        query_embedding: list[float],
        model: str,
        dimensions: int,
        top_k: int = 5,
        organization_id: int | None = None,
    ) -> list[SimilaritySearchResult]:
        if dimensions <= 0:
            raise ValueError(
                "dimensions must be greater than zero."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if len(query_embedding) != dimensions:
            raise ValueError(
                "Query embedding dimensions do not match configuration: "
                f"expected {dimensions}, "
                f"got {len(query_embedding)}."
            )

        distance = DocumentChunkEmbedding.embedding.cosine_distance(
            query_embedding,
        )

        statement = (
            select(
                DocumentChunkEmbedding,
                distance.label("distance"),
            )
            .where(
                DocumentChunkEmbedding.model == model,
                DocumentChunkEmbedding.dimensions == dimensions,
            )
            .order_by(distance)
            .limit(top_k)
        )

        scope = tenant_options(organization_id)
        if scope:
            statement = statement.where(text("""
                EXISTS (
                    SELECT 1 FROM core_documentchunk c
                    JOIN core_document d ON d.id = c.document_id
                    WHERE c.id = document_chunk_embeddings.document_chunk_id
                      AND d.organization_id = :organization_id
                      AND d.status = 'ready' AND d.embedding_status = 'ready'
                )
            """).bindparams(**scope))
        else:
            statement = statement.where(text("FALSE"))

        rows = db.execute(statement).all()

        return [
            SimilaritySearchResult(
                embedding=embedding,
                distance=float(distance_value),
                similarity=1.0 - float(distance_value),
            )
            for embedding, distance_value in rows
        ]
