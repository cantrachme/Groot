from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..embeddings import EmbeddingConfig, EmbeddingProvider
from .similarity_search_service import (
    SimilaritySearchResult,
    SimilaritySearchService,
)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    results: tuple[SimilaritySearchResult, ...]


class RetrievalService:
    """Embeds a query and retrieves the most similar document chunks."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        config: EmbeddingConfig,
        similarity_search: SimilaritySearchService | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.similarity_search = (
            similarity_search
            or SimilaritySearchService()
        )

    def retrieve(
        self,
        db: Session,
        query: str,
        top_k: int = 5,
    ) -> RetrievalResult:
        if not query.strip():
            raise ValueError(
                "query must not be empty."
            )

        query_embedding = self.provider.embed_text(query)

        results = self.similarity_search.search(
            db=db,
            query_embedding=query_embedding,
            model=self.config.model,
            dimensions=self.config.dimensions,
            top_k=top_k,
        )

        return RetrievalResult(
            query=query,
            results=tuple(results),
        )
