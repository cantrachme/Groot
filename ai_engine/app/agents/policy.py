from .agent import Agent
from .capabilities import AgentToolAccessError, ToolPermission
from .context import AgentContext


class AgentCapabilityPolicy:
    """Enforces agent tool access and execution permissions."""

    def __init__(
        self,
        permissions: tuple[ToolPermission, ...] = (),
    ) -> None:
        self._permissions = {
            item.tool_name: item.permission
            for item in permissions
        }

    def authorize(
        self,
        agent: Agent,
        tool_name: str,
        context: AgentContext,
    ) -> None:
        if tool_name not in agent.allowed_tools:
            raise AgentToolAccessError(
                f"Agent '{agent.name}' is not allowed to use "
                f"tool '{tool_name}'."
            )

        required_permission = self._permissions.get(tool_name)

        if (
            required_permission is not None
            and required_permission not in context.permissions
        ):
            raise AgentToolAccessError(
                f"Agent '{agent.name}' lacks permission "
                f"'{required_permission}' for tool '{tool_name}'."
            )
