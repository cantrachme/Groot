from typing import TYPE_CHECKING

from .models import ActionRequest, ActionResult

if TYPE_CHECKING:
    from ..agents.context import AgentContext
    from .registry import ActionRegistry


class ActionNotApprovedError(PermissionError):
    """Raised when an action is executed without approval."""


class ActionExecutionError(RuntimeError):
    """A registered handler failed without exposing its exception message."""


class ActionExecutor:
    """Executes approved actions."""

    def __init__(self, registry: "ActionRegistry | None" = None) -> None:
        self.registry = registry

    def execute(
        self,
        request: ActionRequest,
        *,
        context: "AgentContext | None" = None,
    ) -> ActionResult:
        if request.approved is not True:
            raise ActionNotApprovedError(
                f"Action not approved: {request.action_name}",
            )

        success = True
        parameters = request.parameters
        if self.registry is not None:
            definition = self.registry.get(request.action_name)
            if context is None or request.tool_name != definition.tool_name:
                raise ValueError("Action execution context or tool mismatch.")
            try:
                success = definition.execute(request, context) is True
            except Exception as exc:
                raise ActionExecutionError("Action execution failed.") from exc
            # Controlled execution never returns input payloads or callback output.
            parameters = {}
        return ActionResult(
            action_name=request.action_name,
            tool_name=request.tool_name,
            parameters=parameters,
            success=success,
        )
