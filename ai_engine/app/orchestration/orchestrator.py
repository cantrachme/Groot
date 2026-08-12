from ..core.context import AIRequestContext
from ..llm.provider import LLMProvider


class Orchestrator:
    def __init__(self, llm_provider: LLMProvider) -> None:
        self.llm_provider = llm_provider

    def handle(self, context: AIRequestContext, message: str) -> str:
        return self.llm_provider.generate(
            system_prompt="You are GROOT, an operational intelligence assistant for a startup.",
            user_message=message,
        )
