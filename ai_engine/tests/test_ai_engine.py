import unittest
from uuid import uuid4

from ai_engine.app.core.context import AIRequestContext
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.llm.tool_call import ToolCall
from ai_engine.app.orchestration.orchestrator import Orchestrator
from ai_engine.app.services.ai_service import AIService
from ai_engine.app.tools import tool_registry


class FakeLLMProvider:
    def __init__(self):
        self.calls = []

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            (
                system_prompt,
                user_message,
                tools,
            )
        )

        return LLMResponse(
            text="FAKE LLM RESPONSE",
            tool_calls=(),
        )


class AIEngineTests(unittest.TestCase):
    def test_ai_request_context(self):
        user_id = uuid4()
        organization_id = uuid4()
        request_id = uuid4()

        context = AIRequestContext(
            user_id=user_id,
            organization_id=organization_id,
            request_id=request_id,
        )

        self.assertEqual(context.user_id, user_id)
        self.assertEqual(context.organization_id, organization_id)
        self.assertEqual(context.request_id, request_id)

    def test_orchestrator_uses_llm_provider_and_registry(self):
        provider = FakeLLMProvider()

        context = AIRequestContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
        )

        response = Orchestrator(
            provider,
            tool_registry,
        ).handle(
            context,
            "Hello GROOT",
        )

        self.assertEqual(response.text, "FAKE LLM RESPONSE")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0][1], "Hello GROOT")
        self.assertIsNotNone(provider.calls[0][2])
        self.assertIn("health_check", tool_registry.list())

    def test_orchestrator_returns_llm_response(self):
        provider = FakeLLMProvider()

        context = AIRequestContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
        )

        response = Orchestrator(
            provider,
            tool_registry,
        ).handle(
            context,
            "Hello GROOT",
        )

        self.assertIsInstance(response, LLMResponse)
        self.assertEqual(response.text, "FAKE LLM RESPONSE")
        self.assertEqual(response.tool_calls, ())

    def test_ai_service_uses_llm_provider(self):
        provider = FakeLLMProvider()

        context = AIRequestContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
        )

        response = AIService(
            provider,
            tool_registry,
        ).handle(
            context,
            "Hello GROOT",
        )

        self.assertIsInstance(response, LLMResponse)
        self.assertEqual(response.text, "FAKE LLM RESPONSE")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0][1], "Hello GROOT")


if __name__ == "__main__":
    unittest.main()


class FakeTool:
    name = "fake_tool"
    description = "Fake tool for testing."

    def __init__(self):
        self.executed = False
        self.arguments = None

    def execute(self, **kwargs):
        self.executed = True
        self.arguments = kwargs
        return {"status": "executed"}


class ToolCallingFakeLLMProvider(FakeLLMProvider):
    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        tool_results: list[dict] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            (
                system_prompt,
                user_message,
                tools,
                tool_results,
            )
        )

        if tool_results:
            return LLMResponse(
                text="GROOT is healthy and operational.",
                tool_calls=(),
            )

        return LLMResponse(
            text="",
            tool_calls=(
                ToolCall(
                    id="test-call-1",
                    name="health_check",
                    arguments={},
                ),
            ),
        )


class ToolExecutionTests(unittest.TestCase):
    def test_orchestrator_executes_requested_tool(self):
        provider = ToolCallingFakeLLMProvider()

        context = AIRequestContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
        )

        response = Orchestrator(
            provider,
            tool_registry,
        ).handle(
            context,
            "Check whether GROOT is healthy.",
        )

        self.assertEqual(response.text, "GROOT is healthy and operational.")
        self.assertEqual(response.tool_calls, ())


if __name__ == "__main__":
    unittest.main()
