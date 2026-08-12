from uuid import UUID

from fastapi import FastAPI
from pydantic import BaseModel

from .core.context import AIRequestContext
from .services.ai_service import AIService


app = FastAPI(
    title="GROOT AI Engine",
    version="0.1.0",
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


@app.post("/ai")
async def process_ai_request(request: AIRequest):
    context = AIRequestContext(
        user_id=request.user_id,
        organization_id=request.organization_id,
        request_id=request.request_id,
    )

    response = AIService().handle(context, request.message)

    return {
        "response": response,
    }
