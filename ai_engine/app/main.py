from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.context import AIRequestContext
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

    response = AIService().handle(context, request.message)

    return response
