import json
import os

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq

from ..provider import LLMProvider
from ..response import LLMResponse
from ..tool_call import ToolCall


class LangChainGroqProvider(LLMProvider):
    """GROOT LLMProvider adapter backed by LangChain ChatGroq."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-120b",
        temperature: float = 0.0,
        api_key: str | None = None,
    ) -> None:
        resolved_api_key = api_key or os.getenv("GROQ_API_KEY")

        if not resolved_api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = ChatGroq(
            model=model,
            temperature=temperature,
            api_key=resolved_api_key,
        )

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        tool_results: list[dict] | None = None,
    ) -> LLMResponse:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        if tool_results:
            assistant_tool_calls = [
                {
                    "name": result["name"],
                    "args": result["arguments"],
                    "id": result["tool_call_id"],
                    "type": "tool_call",
                }
                for result in tool_results
            ]

            messages.append(
                AIMessage(
                    content="",
                    tool_calls=assistant_tool_calls,
                )
            )

            for result in tool_results:
                messages.append(
                    ToolMessage(
                        content=result["content"],
                        tool_call_id=result["tool_call_id"],
                    )
                )

        client = self.client

        if tools:
            client = client.bind_tools(tools)

        response = client.invoke(messages)

        return self._to_llm_response(response)

    @staticmethod
    def _to_llm_response(response: AIMessage) -> LLMResponse:
        tool_calls = tuple(
            ToolCall(
                id=tool_call["id"],
                name=tool_call["name"],
                arguments=tool_call["args"],
            )
            for tool_call in response.tool_calls
        )

        if isinstance(response.content, str):
            text = response.content
        elif response.content is None:
            text = ""
        else:
            text = str(response.content)

        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
        )
