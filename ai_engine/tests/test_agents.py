import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentNotFoundError,
    AgentRegistry,
    AgentResult,
)


class FakeAgent(Agent):
    name = "fake_agent"
    description = "Fake agent used for testing."
    capabilities = (
        "testing",
        "validation",
    )
    allowed_tools = (
        "health_check",
    )

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            agent_name=self.name,
            summary=f"Completed: {context.task}",
            data={"task": context.task},
            confidence=0.95,
        )


class AgentContextTests(unittest.TestCase):
    def test_context_stores_execution_data(self):
        user_id = uuid4()
        organization_id = uuid4()
        request_id = uuid4()

        context = AgentContext(
            user_id=user_id,
            organization_id=organization_id,
            request_id=request_id,
            task="Analyze revenue",
            state={"step": 1},
            permissions=frozenset({"finance.read"}),
        )

        self.assertEqual(context.user_id, user_id)
        self.assertEqual(
            context.organization_id,
            organization_id,
        )
        self.assertEqual(context.request_id, request_id)
        self.assertEqual(context.task, "Analyze revenue")
        self.assertEqual(context.state, {"step": 1})
        self.assertEqual(
            context.permissions,
            frozenset({"finance.read"}),
        )


class AgentResultTests(unittest.TestCase):
    def test_result_stores_standardized_output(self):
        result = AgentResult(
            success=True,
            agent_name="fake_agent",
            summary="Completed analysis.",
            data={"value": 42},
            confidence=0.9,
            evidence=("source-1",),
            tool_calls=(
                {"name": "health_check"},
            ),
            metadata={"duration_ms": 10},
        )

        self.assertTrue(result.success)
        self.assertEqual(
            result.agent_name,
            "fake_agent",
        )
        self.assertEqual(
            result.summary,
            "Completed analysis.",
        )
        self.assertEqual(
            result.data,
            {"value": 42},
        )
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(
            result.evidence,
            ("source-1",),
        )
        self.assertEqual(
            result.tool_calls,
            ({"name": "health_check"},),
        )
        self.assertEqual(
            result.metadata,
            {"duration_ms": 10},
        )


class AgentRegistryTests(unittest.TestCase):
    def test_register_and_get_agent(self):
        registry = AgentRegistry()
        agent = FakeAgent()

        registry.register(agent)

        self.assertTrue(
            registry.has("fake_agent"),
        )
        self.assertIs(
            registry.get("fake_agent"),
            agent,
        )
        self.assertEqual(
            registry.list(),
            ["fake_agent"],
        )

    def test_rejects_duplicate_agent(self):
        registry = AgentRegistry()

        registry.register(FakeAgent())

        with self.assertRaisesRegex(
            ValueError,
            "Agent already registered: fake_agent",
        ):
            registry.register(FakeAgent())

    def test_unknown_agent_raises_agent_not_found(self):
        registry = AgentRegistry()

        with self.assertRaisesRegex(
            AgentNotFoundError,
            "Agent not found: missing_agent",
        ):
            registry.get("missing_agent")


class AgentExecutionTests(unittest.TestCase):
    def test_agent_returns_standardized_result(self):
        agent = FakeAgent()

        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Analyze revenue",
        )

        result = agent.execute(context)

        self.assertIsInstance(
            result,
            AgentResult,
        )
        self.assertTrue(result.success)
        self.assertEqual(
            result.agent_name,
            "fake_agent",
        )
        self.assertEqual(
            result.data,
            {"task": "Analyze revenue"},
        )


if __name__ == "__main__":
    unittest.main()
