from ..core.context import AIRequestContext


class Orchestrator:
    def handle(self, context: AIRequestContext, message: str) -> str:
        return "GROOT Orchestrator received the request."
