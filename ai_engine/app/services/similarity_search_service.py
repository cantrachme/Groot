from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import DocumentChunkEmbedding


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

        rows = db.execute(statement).all()

        return [
            SimilaritySearchResult(
                embedding=embedding,
                distance=float(distance_value),
                similarity=1.0 - float(distance_value),
            )
            for embedding, distance_value in rows
        ]
