from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPermission:
    """Permission required to execute a specific tool."""

    tool_name: str
    permission: str


class AgentToolAccessError(PermissionError):
    """Raised when an agent is not allowed to use a tool."""
