from ..core.context import AIRequestContext


class AIService:
    def handle(self, context: AIRequestContext, message: str) -> str:
        return "AI Engine received the request."
