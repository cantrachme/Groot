import json
import os

from groq import Groq

from ..provider import LLMProvider
from ..response import LLMResponse
from ..tool_call import ToolCall


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=api_key)

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        tool_results: list[dict] | None = None,
    ) -> LLMResponse:
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        if tool_results:
            assistant_tool_calls = []

            for result in tool_results:
                assistant_tool_calls.append(
                    {
                        "id": result["tool_call_id"],
                        "type": "function",
                        "function": {
                            "name": result["name"],
                            "arguments": json.dumps(result["arguments"]),
                        },
                    }
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": assistant_tool_calls,
                }
            )

            for result in tool_results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"],
                    }
                )

        request = {
            "model": "openai/gpt-oss-120b",
            "messages": messages,
        }

        if tools:
            request["tools"] = tools
            request["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**request)
        message = response.choices[0].message

        tool_calls = tuple(
            ToolCall(
                id=tool_call.id,
                name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
            for tool_call in (message.tool_calls or [])
        )

        return LLMResponse(
            text=message.content or "",
            tool_calls=tool_calls,
        )
