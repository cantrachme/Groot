import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentRegistry,
    AgentResult,
    AgentSelection,
    AgentSupervisor,
    MultiAgentCoordinator,
)


class RecordingAgent(Agent):
    def __init__(self, name: str) -> None:
        self.name = name
        self.description = f"{name} test agent."
        self.capabilities = ("testing",)
        self.allowed_tools = ()
        self.received_contexts = []

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        self.received_contexts.append(context)

        return AgentResult(
            success=True,
            agent_name=self.name,
            summary=f"Completed by {self.name}.",
            data={
                "task": context.task,
            },
        )


class MultiAgentCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()

        self.supervisor = AgentSupervisor(
            self.registry,
        )

        self.coordinator = MultiAgentCoordinator(
            self.supervisor,
        )

        self.context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Investigate revenue decline",
        )

    def test_coordinates_multiple_agents(self):
        finance_agent = RecordingAgent(
            "finance_agent",
        )

        sales_agent = RecordingAgent(
            "sales_agent",
        )

        research_agent = RecordingAgent(
            "research_agent",
        )

        self.registry.register(finance_agent)
        self.registry.register(sales_agent)
        self.registry.register(research_agent)

        selection = AgentSelection(
            agent_names=(
                "finance_agent",
                "sales_agent",
                "research_agent",
            ),
            reason="Revenue investigation requires multiple agents.",
        )

        coordination = self.coordinator.execute(
            selection,
            self.context,
        )

        self.assertEqual(
            coordination.selection,
            selection,
        )

        self.assertEqual(
            tuple(
                result.agent_name
                for result in coordination.results
            ),
            (
                "finance_agent",
                "sales_agent",
                "research_agent",
            ),
        )

    def test_preserves_original_context_for_all_agents(self):
        first_agent = RecordingAgent(
            "first_agent",
        )

        second_agent = RecordingAgent(
            "second_agent",
        )

        self.registry.register(first_agent)
        self.registry.register(second_agent)

        selection = AgentSelection(
            agent_names=(
                "first_agent",
                "second_agent",
            ),
            reason="Both agents require the same investigation context.",
        )

        self.coordinator.execute(
            selection,
            self.context,
        )

        self.assertIs(
            first_agent.received_contexts[0],
            self.context,
        )

        self.assertIs(
            second_agent.received_contexts[0],
            self.context,
        )

    def test_empty_selection_returns_empty_results(self):
        selection = AgentSelection(
            agent_names=(),
            reason="No agents required.",
        )

        coordination = self.coordinator.execute(
            selection,
            self.context,
        )

        self.assertEqual(
            coordination.results,
            (),
        )


if __name__ == "__main__":
    unittest.main()
