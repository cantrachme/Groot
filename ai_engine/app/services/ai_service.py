from ..core.context import AIRequestContext
from ..orchestration.orchestrator import Orchestrator


class AIService:
    def handle(self, context: AIRequestContext, message: str) -> str:
        return Orchestrator().handle(context, message)
