from .agent import Agent
from .exceptions import AgentNotFoundError


class AgentRegistry:
    """Registry of available GROOT agents."""

    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        if agent.name in self._agents:
            raise ValueError(
                f"Agent already registered: {agent.name}"
            )

        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise AgentNotFoundError(
                f"Agent not found: {name}"
            ) from exc

    def has(self, name: str) -> bool:
        return name in self._agents

    def list(self) -> list[str]:
        return list(self._agents.keys())
