from ai_engine.app.actions import ActionResult

from .models import VerificationResult


class ActionVerifier:
    """Verifies whether an action completed successfully."""

    def verify(
        self,
        action_result: ActionResult,
    ) -> VerificationResult:
        return VerificationResult(
            action_name=action_result.action_name,
            verified=action_result.success,
            details=(
                "Action completed successfully."
                if action_result.success
                else "Action execution failed."
            ),
        )
