from typing import Any

from .agent import Agent
from .context import AgentContext
from .result import AgentResult


class ResearchAgent(Agent):
    """Agent responsible for research and evidence-based analysis."""

    name = "research_agent"

    description = (
        "Researches information, gathers evidence, compares findings, "
        "summarizes results, and preserves source citations."
    )

    capabilities = (
        "research",
        "gather_evidence",
        "compare_information",
        "summarize",
        "cite_sources",
    )

    allowed_tools = ()

    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:
        evidence = tuple(
            context.state.get("evidence", ())
        )

        citations = tuple(
            context.state.get("citations", ())
        )

        comparison = context.state.get(
            "comparison",
        )

        summary = context.state.get(
            "summary",
            f"Research completed: {context.task}",
        )

        data: dict[str, Any] = {
            "task": context.task,
            "comparison": comparison,
            "citations": citations,
        }

        return AgentResult(
            success=True,
            agent_name=self.name,
            summary=summary,
            data=data,
            evidence=evidence,
            metadata={
                "capabilities": self.capabilities,
            },
        )
