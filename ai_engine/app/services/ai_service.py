from sqlalchemy.orm import Session

from ..core.context import AIRequestContext
from ..embeddings import (
    EmbeddingConfig,
    EmbeddingProvider,
    LocalEmbeddingProvider,
)
from ..llm.provider import LLMProvider
from ..llm.response import LLMResponse
from ..llm.providers.groq import GroqProvider
from ..orchestration.orchestrator import Orchestrator
from ..tools import tool_registry
from ..tools.registry import ToolRegistry
from .rag_document_service import RAGDocumentService
from .rag_document_service import RAGDocumentService
from .rag_service import RAGResponse, RAGService


class AIService:
    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        registry: ToolRegistry | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        embedding_config: EmbeddingConfig | None = None,
    ) -> None:
        self.llm_provider = llm_provider or GroqProvider()

        self.orchestrator = Orchestrator(
            self.llm_provider,
            registry or tool_registry,
        )

        self.embedding_config = embedding_config or EmbeddingConfig.from_env()
        self.embedding_provider = (
            embedding_provider
            or LocalEmbeddingProvider(self.embedding_config)
        )
        self.rag_document_service = RAGDocumentService()

    def handle(
        self,
        context: AIRequestContext,
        message: str,
    ) -> LLMResponse:
        return self.orchestrator.handle(context, message)

    def handle_rag(
        self,
        context: AIRequestContext,
        db: Session,
        message: str,
        top_k: int = 5,
    ) -> RAGResponse:
        if self.embedding_provider is None:
            raise RuntimeError(
                "An embedding provider is required for RAG requests."
            )

        retrieval_service = RAGService(
            llm_provider=self.llm_provider,
            embedding_provider=self.embedding_provider,
            embedding_config=self.embedding_config,
        )

        retrieval = retrieval_service.retrieval_service.retrieve(
            db=db,
            query=message,
            top_k=top_k,
        )

        chunk_ids = [
            result.embedding.document_chunk_id
            for result in retrieval.results
        ]

        chunk_texts = self.rag_document_service.get_chunk_texts(
            db=db,
            chunk_ids=chunk_ids,
        )

        return retrieval_service.answer(
            db=db,
            query=message,
            chunk_texts=chunk_texts,
            top_k=top_k,
        )
