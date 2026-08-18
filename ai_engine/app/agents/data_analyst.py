from .agent import Agent
from .context import AgentContext
from .result import AgentResult


class DataAnalystAgent(Agent):
    """Agent responsible for structured data analysis."""

    name = "data_analyst_agent"

    description = (
        "Analyzes structured company data, calculates metrics, "
        "performs calculations, and identifies trends."
    )

    capabilities = (
        "query_structured_data",
        "calculate_metrics",
        "perform_calculations",
        "analyze_trends",
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
                f"Data analysis completed: {context.task}"
            ),
            data={
                "task": context.task,
            },
            metadata={
                "capabilities": self.capabilities,
            },
        )
