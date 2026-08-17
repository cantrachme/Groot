from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..embeddings import EmbeddingConfig, EmbeddingProvider
from ..llm.provider import LLMProvider
from ..llm.response import LLMResponse
from .context_assembly_service import (
    AssembledContext,
    ContextAssemblyService,
)
from .retrieval_service import RetrievalService


@dataclass(frozen=True)
class RAGResponse:
    query: str
    context: AssembledContext
    response: LLMResponse


class RAGService:
    """Retrieves relevant document context and generates an LLM answer."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        embedding_provider: EmbeddingProvider,
        embedding_config: EmbeddingConfig,
        retrieval_service: RetrievalService | None = None,
        context_assembly: ContextAssemblyService | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.retrieval_service = (
            retrieval_service
            or RetrievalService(
                provider=embedding_provider,
                config=embedding_config,
            )
        )
        self.context_assembly = (
            context_assembly
            or ContextAssemblyService()
        )

    def answer(
        self,
        db: Session,
        query: str,
        chunk_texts: dict[int, str],
        top_k: int = 5,
    ) -> RAGResponse:
        if not query.strip():
            raise ValueError(
                "query must not be empty."
            )

        retrieval = self.retrieval_service.retrieve(
            db=db,
            query=query,
            top_k=top_k,
        )

        context = self.context_assembly.assemble(
            results=list(retrieval.results),
            chunk_texts=chunk_texts,
        )

        response = self.llm_provider.generate(
            system_prompt=(
                "You are GROOT, an operational intelligence assistant. "
                "Answer the user's question using the provided document "
                "context. If the context does not contain enough "
                "information to answer, say so instead of inventing facts."
            ),
            user_message=(
                f"User question:\n{query}\n\n"
                f"Document context:\n"
                f"{context.text}"
            ),
        )

        return RAGResponse(
            query=query,
            context=context,
            response=response,
        )
