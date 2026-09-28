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
        *,
        capture_failures: bool = False,
    ) -> tuple[AgentResult, ...]:
        results = []

        for agent_name in selection.agent_names:
            try:
                agent = self.registry.get(agent_name)
                graph = AgentGraph(agent)
                result = graph.invoke(context)
                if capture_failures and (
                    not isinstance(result, AgentResult)
                    or result.agent_name != agent_name
                ):
                    raise ValueError("Agent returned an invalid result identity.")
            except Exception as exc:
                if not capture_failures:
                    raise
                # Exception messages can contain provider credentials or SQL inputs.
                # Preserve failure type without forwarding those messages to synthesis.
                result = AgentResult(
                    success=False,
                    agent_name=agent_name,
                    summary="Agent execution failed.",
                    errors=(f"Agent execution failed ({type(exc).__name__}).",),
                )

            results.append(result)

        return tuple(results)
