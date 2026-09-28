from .models import ActionRisk, ApprovalRequirement


class ApprovalPolicy:
    """Determines whether an action requires human approval."""

    def evaluate(
        self,
        action_name: str,
        risk: ActionRisk,
    ) -> ApprovalRequirement:
        if not isinstance(risk, ActionRisk):
            raise TypeError("Unknown action risk.")
        return ApprovalRequirement(
            action_name=action_name,
            risk=risk,
            approval_required=(risk is ActionRisk.HIGH_IMPACT),
        )
