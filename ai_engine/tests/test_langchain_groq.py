import unittest
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage

from ai_engine.app.llm.providers.langchain_groq import (
    LangChainGroqProvider,
)


class LangChainGroqProviderTests(unittest.TestCase):
    @patch(
        "ai_engine.app.llm.providers.langchain_groq.ChatGroq"
    )
    def test_generates_llm_response(
        self,
        chat_groq,
    ):
        client = chat_groq.return_value

        client.invoke.return_value = AIMessage(
            content="Hello from GROOT.",
        )

        provider = LangChainGroqProvider(
            api_key="test-key",
        )

        result = provider.generate(
            system_prompt="You are GROOT.",
            user_message="Hello",
        )

        self.assertEqual(
            result.text,
            "Hello from GROOT.",
        )
        self.assertEqual(
            result.tool_calls,
            (),
        )

        client.invoke.assert_called_once()

    @patch(
        "ai_engine.app.llm.providers.langchain_groq.ChatGroq"
    )
    def test_converts_tool_calls(
        self,
        chat_groq,
    ):
        client = chat_groq.return_value

        bound_client = client.bind_tools.return_value

        bound_client.invoke.return_value = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "health_check",
                    "args": {},
                    "id": "call-1",
                }
            ],
        )

        provider = LangChainGroqProvider(
            api_key="test-key",
        )

        result = provider.generate(
            system_prompt="Use tools.",
            user_message="Check health.",
            tools=[
                {
                    "name": "health_check",
                    "description": "Check system health.",
                }
            ],
        )

        self.assertEqual(
            len(result.tool_calls),
            1,
        )

        self.assertEqual(
            result.tool_calls[0].id,
            "call-1",
        )
        self.assertEqual(
            result.tool_calls[0].name,
            "health_check",
        )
        self.assertEqual(
            result.tool_calls[0].arguments,
            {},
        )

        client.bind_tools.assert_called_once()

    @patch(
        "ai_engine.app.llm.providers.langchain_groq.ChatGroq"
    )
    def test_requires_api_key(
        self,
        chat_groq,
    ):
        with patch.dict(
            "os.environ",
            {},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "GROQ_API_KEY is not configured",
            ):
                LangChainGroqProvider()

        chat_groq.assert_not_called()


if __name__ == "__main__":
    unittest.main()
