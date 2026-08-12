import unittest
from uuid import uuid4

from ai_engine.app.core.context import AIRequestContext
from ai_engine.app.orchestration.orchestrator import Orchestrator
from ai_engine.app.services.ai_service import AIService
from ai_engine.app.tools import tool_registry


class FakeLLMProvider:
    def __init__(self):
        self.calls = []

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.calls.append((system_prompt, user_message))
        return "FAKE LLM RESPONSE"


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

        self.assertEqual(response, "FAKE LLM RESPONSE")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0][1], "Hello GROOT")
        self.assertIn("health_check", tool_registry.list())

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

        self.assertEqual(response, "FAKE LLM RESPONSE")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(provider.calls[0][1], "Hello GROOT")


if __name__ == "__main__":
    unittest.main()
