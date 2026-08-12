from ..core.context import AIRequestContext
from ..llm.provider import LLMProvider
from ..llm.providers.groq import GroqProvider
from ..orchestration.orchestrator import Orchestrator


class AIService:
    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.orchestrator = Orchestrator(
            llm_provider or GroqProvider()
        )

    def handle(self, context: AIRequestContext, message: str) -> str:
        return self.orchestrator.handle(context, message)
