import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentResult,
    OperationsAgent,
)


class OperationsAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = OperationsAgent()

        self.context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Analyze current operational status.",
        )

    def test_implements_agent_contract(self):
        self.assertIsInstance(
            self.agent,
            Agent,
        )

    def test_defines_operations_capabilities(self):
        self.assertEqual(
            self.agent.capabilities,
            (
                "analyze_projects",
                "analyze_tasks",
                "analyze_events",
                "analyze_risks",
                "analyze_integrations",
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
            "operations_agent",
        )

        self.assertEqual(
            result.summary,
            (
                "Operations analysis completed: "
                "Analyze current operational status."
            ),
        )

    def test_preserves_task_in_result_data(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertEqual(
            result.data,
            {
                "task": "Analyze current operational status.",
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
