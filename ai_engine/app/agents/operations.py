from .agent import Agent
from .context import AgentContext
from .result import AgentResult


class OperationsAgent(Agent):
    """Agent responsible for operational company analysis."""

    name = "operations_agent"

    description = (
        "Analyzes operational company data including projects, tasks, "
        "events, risks, and integrations."
    )

    capabilities = (
        "analyze_projects",
        "analyze_tasks",
        "analyze_events",
        "analyze_risks",
        "analyze_integrations",
    )

    allowed_tools = ()

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        return AgentResult(
            success=True,
            agent_name=self.name,
            summary=(
                f"Operations analysis completed: {context.task}"
            ),
            data={
                "task": context.task,
            },
            metadata={
                "capabilities": self.capabilities,
            },
        )
