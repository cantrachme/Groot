from collections.abc import Callable

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..services.rag_service import RAGService
from ..tools.registry import ToolRegistry
from .agent import Agent
from .context import AgentContext
from .result import AgentResult


class KnowledgeAgent(Agent):
    """Agent responsible for retrieving and answering from internal knowledge."""

    name = "knowledge_agent"

    description = (
        "Searches internal documents, retrieves relevant knowledge, "
        "answers questions from retrieved context, and preserves "
        "document evidence."
    )

    capabilities = (
        "search_documents",
        "retrieve_report",
        "search_company_knowledge",
    )

    allowed_tools = ("list_documents", "read_document_chunks")

    def __init__(
        self,
        rag_service: RAGService,
    ) -> None:
        self.rag_service = rag_service

    def read_only_tools(
        self,
        context: AgentContext,
        credentials: HTTPAuthorizationCredentials | None,
        *,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> ToolRegistry:
        """Bind tools for a trusted caller or the existing tool orchestrator."""
        from ..tools.read_only import build_read_only_registry

        return build_read_only_registry(
            credentials=credentials,
            agent=self,
            context=context,
            session_factory=session_factory,
        )

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        db = context.state.get("db")

        if not isinstance(db, Session):
            return AgentResult(
                success=False,
                agent_name=self.name,
                summary="Knowledge retrieval requires a database session.",
                errors=(
                    "A SQLAlchemy Session must be provided in "
                    "context.state['db'].",
                ),
            )

        query = context.state.get(
            "query",
            context.task,
        )

        top_k = context.state.get(
            "top_k",
            5,
        )

        rag_response = self.rag_service.answer(
            db=db,
            query=query,
            top_k=top_k,
            **({"organization_id": context.organization_id}
               if type(context.organization_id) is int else {}),
        )

        evidence = tuple(
            {
                "document_chunk_id": item.document_chunk_id,
                "text": item.text,
                "similarity": item.similarity,
            }
            for item in rag_response.context.items
        )

        citations = tuple(
            item.document_chunk_id
            for item in rag_response.context.items
        )

        return AgentResult(
            success=True,
            agent_name=self.name,
            summary=rag_response.response.text,
            data={
                "query": query,
                "answer": rag_response.response.text,
                "citations": citations,
            },
            evidence=evidence,
            metadata={
                "capabilities": self.capabilities,
                "top_k": top_k,
                "context": rag_response.context.text,
            },
        )
