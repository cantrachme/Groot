from .models import ActionRequest, ActionResult


class ActionNotApprovedError(PermissionError):
    """Raised when an action is executed without approval."""


class ActionExecutor:
    """Executes approved actions."""

    def execute(
        self,
        request: ActionRequest,
    ) -> ActionResult:
        if not request.approved:
            raise ActionNotApprovedError(
                f"Action not approved: {request.action_name}",
            )

        return ActionResult(
            action_name=request.action_name,
            tool_name=request.tool_name,
            parameters=request.parameters,
            success=True,
        )
