from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .core.context import AIRequestContext
from .db.dependencies import get_db
from .llm.response import LLMResponse
from .services.ai_service import AIService


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


class RAGRequest(AIRequest):
    top_k: int = 5


class RAGResponsePayload(BaseModel):
    query: str
    context: str
    response: LLMResponse


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
async def process_rag_request(
    request: RAGRequest,
    db: Session = Depends(get_db),
):
    context = AIRequestContext(
        user_id=request.user_id,
        organization_id=request.organization_id,
        request_id=request.request_id,
    )

    service = AIService()

    rag_result = service.handle_rag(
        context=context,
        db=db,
        message=request.message,
        top_k=request.top_k,
    )

    return RAGResponsePayload(
        query=rag_result.query,
        context=rag_result.context.text,
        response=rag_result.response,
    )
