from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from .agents.context import AgentContext
from .agents.knowledge import KnowledgeAgent
from .core.authentication import KnowledgeIdentity, authenticate_knowledge
from .core.context import AIRequestContext
from .db.dependencies import get_db
from .llm.response import LLMResponse
from .services.ai_service import AIService
from .services.context_assembly_service import ContextItem
from .services.rag_service import RAGService

app = FastAPI(
    title="GROOT AI Engine",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class AIRequest(BaseModel):
    user_id: UUID
    organization_id: UUID
    request_id: UUID
    message: str


class RAGRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    message: str = Field(min_length=1, max_length=12000)
    top_k: int = Field(default=5, ge=1, le=50)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class RAGResponsePayload(BaseModel):
    query: str
    context: str
    response: LLMResponse
    evidence: list[ContextItem]
    citations: list[int]


def get_knowledge_agent() -> KnowledgeAgent:
    service = AIService()
    return KnowledgeAgent(RAGService(
        llm_provider=service.llm_provider,
        embedding_provider=service.embedding_provider,
        embedding_config=service.embedding_config,
    ))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ai-engine",
    }


@app.post("/ai", response_model=LLMResponse)
async def process_ai_request(request: AIRequest):
    context = AIRequestContext(
        user_id=request.user_id,
        organization_id=request.organization_id,
        request_id=request.request_id,
    )

    return AIService().handle(
        context,
        request.message,
    )


@app.post("/rag", response_model=RAGResponsePayload)
def process_rag_request(
    request: RAGRequest,
    identity: Annotated[KnowledgeIdentity, Depends(authenticate_knowledge)],
    db: Annotated[Session, Depends(get_db)],
    agent: Annotated[KnowledgeAgent, Depends(get_knowledge_agent)],
):
    context = AgentContext(
        user_id=identity.user_id,
        organization_id=identity.organization_id,
        request_id=request.request_id,
        task=request.message,
        state={"db": db, "top_k": request.top_k},
        permissions=frozenset({"knowledge.read"}),
    )
    result = agent.execute(context)

    return RAGResponsePayload(
        query=result.data["query"],
        context=result.metadata["context"],
        response=LLMResponse(text=result.summary, tool_calls=()),
        evidence=[ContextItem(**item) for item in result.evidence],
        citations=list(result.data["citations"]),
    )
