from dataclasses import dataclass

from .context import AgentContext
from .result import AgentResult
from .supervisor import AgentSelection, AgentSupervisor


@dataclass(frozen=True)
class CoordinationResult:
    """Result produced by a multi-agent coordination run."""

    selection: AgentSelection
    results: tuple[AgentResult, ...]


class MultiAgentCoordinator:
    """Coordinates multiple selected agents for a single investigation."""

    def __init__(
        self,
        supervisor: AgentSupervisor,
    ) -> None:
        self.supervisor = supervisor

    def execute(
        self,
        selection: AgentSelection,
        context: AgentContext,
    ) -> CoordinationResult:
        results = self.supervisor.execute(
            selection,
            context,
        )

        return CoordinationResult(
            selection=selection,
            results=results,
        )
