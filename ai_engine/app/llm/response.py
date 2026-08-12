from dataclasses import dataclass

from .tool_call import ToolCall


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tool_calls: tuple[ToolCall, ...]
