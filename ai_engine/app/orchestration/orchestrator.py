from ..core.context import AIRequestContext
from ..llm.provider import LLMProvider
from ..tools.registry import ToolRegistry


class Orchestrator:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry

    def handle(self, context: AIRequestContext, message: str) -> str:
        return self.llm_provider.generate(
            system_prompt="You are GROOT, an operational intelligence assistant for a startup.",
            user_message=message,
        )
