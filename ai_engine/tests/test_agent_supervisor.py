import unittest
from uuid import uuid4

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentNotFoundError,
    AgentRegistry,
    AgentResult,
    AgentSelection,
    AgentSupervisor,
)


class RecordingAgent(Agent):
    def __init__(
        self,
        name: str,
    ) -> None:
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
            data={"task": context.task},
        )


class AgentSelectionTests(unittest.TestCase):
    def test_selection_stores_agent_names_and_reason(self):
        selection = AgentSelection(
            agent_names=(
                "first_agent",
                "second_agent",
            ),
            reason="Both agents are required.",
        )

        self.assertEqual(
            selection.agent_names,
            (
                "first_agent",
                "second_agent",
            ),
        )
        self.assertEqual(
            selection.reason,
            "Both agents are required.",
        )


class AgentSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        self.supervisor = AgentSupervisor(
            self.registry,
        )

        self.context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Analyze revenue",
        )

    def test_supervisor_executes_one_selected_agent(self):
        agent = RecordingAgent("first_agent")
        self.registry.register(agent)

        selection = AgentSelection(
            agent_names=("first_agent",),
            reason="Single agent required.",
        )

        results = self.supervisor.execute(
            selection,
            self.context,
        )

        self.assertEqual(
            len(results),
            1,
        )
        self.assertEqual(
            results[0].agent_name,
            "first_agent",
        )

    def test_supervisor_executes_multiple_selected_agents(self):
        first_agent = RecordingAgent("first_agent")
        second_agent = RecordingAgent("second_agent")

        self.registry.register(first_agent)
        self.registry.register(second_agent)

        selection = AgentSelection(
            agent_names=(
                "first_agent",
                "second_agent",
            ),
            reason="Multiple agents required.",
        )

        results = self.supervisor.execute(
            selection,
            self.context,
        )

        self.assertEqual(
            len(results),
            2,
        )

        self.assertEqual(
            results[0].agent_name,
            "first_agent",
        )
        self.assertEqual(
            results[1].agent_name,
            "second_agent",
        )

    def test_results_preserve_selection_order(self):
        first_agent = RecordingAgent("first_agent")
        second_agent = RecordingAgent("second_agent")

        self.registry.register(first_agent)
        self.registry.register(second_agent)

        selection = AgentSelection(
            agent_names=(
                "second_agent",
                "first_agent",
            ),
            reason="Order matters.",
        )

        results = self.supervisor.execute(
            selection,
            self.context,
        )

        self.assertEqual(
            tuple(
                result.agent_name
                for result in results
            ),
            (
                "second_agent",
                "first_agent",
            ),
        )

    def test_each_agent_receives_original_context(self):
        first_agent = RecordingAgent("first_agent")
        second_agent = RecordingAgent("second_agent")

        self.registry.register(first_agent)
        self.registry.register(second_agent)

        selection = AgentSelection(
            agent_names=(
                "first_agent",
                "second_agent",
            ),
            reason="Both agents need the same context.",
        )

        self.supervisor.execute(
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

    def test_unknown_selected_agent_raises_agent_not_found(self):
        selection = AgentSelection(
            agent_names=("missing_agent",),
            reason="Test unknown agent.",
        )

        with self.assertRaisesRegex(
            AgentNotFoundError,
            "Agent not found: missing_agent",
        ):
            self.supervisor.execute(
                selection,
                self.context,
            )

    def test_empty_selection_returns_empty_tuple(self):
        selection = AgentSelection(
            agent_names=(),
            reason="No agents required.",
        )

        results = self.supervisor.execute(
            selection,
            self.context,
        )

        self.assertEqual(
            results,
            (),
        )


if __name__ == "__main__":
    unittest.main()
