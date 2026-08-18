import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentGraph,
    AgentResult,
)


class GraphTestAgent(Agent):
    name = "graph_test_agent"
    description = "Agent used to test LangGraph execution."
    capabilities = ("testing",)
    allowed_tools = ()

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            agent_name=self.name,
            summary=f"Completed: {context.task}",
            data={
                "task": context.task,
            },
        )


class AgentGraphTests(unittest.TestCase):
    def test_executes_agent_through_graph(self):
        agent = GraphTestAgent()
        graph = AgentGraph(agent)

        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Analyze startup metrics",
        )

        result = graph.invoke(context)

        self.assertIsInstance(
            result,
            AgentResult,
        )
        self.assertTrue(result.success)
        self.assertEqual(
            result.agent_name,
            "graph_test_agent",
        )
        self.assertEqual(
            result.data,
            {
                "task": "Analyze startup metrics",
            },
        )

    def test_preserves_agent_context(self):
        agent = GraphTestAgent()
        graph = AgentGraph(agent)

        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Inspect financial data",
            state={
                "source": "dashboard",
            },
        )

        result = graph.invoke(context)

        self.assertEqual(
            result.summary,
            "Completed: Inspect financial data",
        )
        self.assertEqual(
            result.data["task"],
            "Inspect financial data",
        )


if __name__ == "__main__":
    unittest.main()
