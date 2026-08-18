import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentResult,
    DataAnalystAgent,
)


class DataAnalystAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = DataAnalystAgent()

        self.context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Analyze current company metrics.",
        )

    def test_implements_agent_contract(self):
        self.assertIsInstance(
            self.agent,
            Agent,
        )

    def test_defines_data_analyst_capabilities(self):
        self.assertEqual(
            self.agent.capabilities,
            (
                "query_structured_data",
                "calculate_metrics",
                "perform_calculations",
                "analyze_trends",
            ),
        )

    def test_returns_standardized_result(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertIsInstance(
            result,
            AgentResult,
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.agent_name,
            "data_analyst_agent",
        )

        self.assertEqual(
            result.summary,
            (
                "Data analysis completed: "
                "Analyze current company metrics."
            ),
        )

    def test_preserves_task_in_result_data(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertEqual(
            result.data,
            {
                "task": "Analyze current company metrics.",
            },
        )

    def test_preserves_capabilities_in_metadata(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertEqual(
            result.metadata,
            {
                "capabilities": self.agent.capabilities,
            },
        )


if __name__ == "__main__":
    unittest.main()
