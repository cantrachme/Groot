from ..core.context import AIRequestContext
from ..llm.provider import LLMProvider
from ..llm.providers.groq import GroqProvider
from ..orchestration.orchestrator import Orchestrator
from ..tools import tool_registry
from ..tools.registry import ToolRegistry


class AIService:
    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.orchestrator = Orchestrator(
            llm_provider or GroqProvider(),
            registry or tool_registry,
        )

    def handle(self, context: AIRequestContext, message: str) -> str:
        return self.orchestrator.handle(context, message)
