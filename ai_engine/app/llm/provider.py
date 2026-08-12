from abc import ABC, abstractmethod

from .response import LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        tool_results: list[dict] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError
