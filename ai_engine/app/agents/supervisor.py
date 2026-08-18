from dataclasses import dataclass

from .context import AgentContext
from .graph import AgentGraph
from .registry import AgentRegistry
from .result import AgentResult


@dataclass(frozen=True)
class AgentSelection:
    """Deterministic selection of agents for execution."""

    agent_names: tuple[str, ...]
    reason: str


class AgentSupervisor:
    """Coordinates execution of selected GROOT agents."""

    def __init__(
        self,
        registry: AgentRegistry,
    ) -> None:
        self.registry = registry

    def execute(
        self,
        selection: AgentSelection,
        context: AgentContext,
    ) -> tuple[AgentResult, ...]:
        results = []

        for agent_name in selection.agent_names:
            agent = self.registry.get(agent_name)

            graph = AgentGraph(agent)

            result = graph.invoke(context)

            results.append(result)

        return tuple(results)
