import json

from ..core.context import AIRequestContext
from ..llm.provider import LLMProvider
from ..llm.response import LLMResponse
from ..tools.registry import ToolRegistry
from ..tools.schema import build_tool_schemas


class Orchestrator:
    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: ToolRegistry,
    ) -> None:
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry

    def handle(
        self,
        context: AIRequestContext,
        message: str,
    ) -> LLMResponse:
        tools = build_tool_schemas(self.tool_registry)

        response = self.llm_provider.generate(
            system_prompt=(
                "You are GROOT, an operational intelligence assistant "
                "for a startup. Use available tools when appropriate."
            ),
            user_message=message,
            tools=tools,
        )

        if not response.tool_calls:
            return response

        tool_results = []

        for tool_call in response.tool_calls:
            tool = self.tool_registry.get(tool_call.name)

            result = tool.execute(**tool_call.arguments)

            tool_results.append(
                {
                    "tool_call_id": tool_call.id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                    "content": json.dumps(result),
                }
            )

        return self.llm_provider.generate(
            system_prompt=(
                "You are GROOT, an operational intelligence assistant "
                "for a startup. Use the tool results to answer the user."
            ),
            user_message=message,
            tools=tools,
            tool_results=tool_results,
        )
