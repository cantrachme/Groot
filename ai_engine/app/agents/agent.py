from abc import ABC, abstractmethod

from .context import AgentContext
from .result import AgentResult


class Agent(ABC):
    """Base contract for all GROOT agents."""

    name: str
    description: str
    capabilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's responsibility."""
        raise NotImplementedError
