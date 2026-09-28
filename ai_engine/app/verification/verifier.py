from typing import TYPE_CHECKING

from ai_engine.app.actions import ActionResult

from .models import VerificationResult

if TYPE_CHECKING:
    from ..actions.registry import ActionRegistry
    from ..agents.context import AgentContext


class ActionVerificationError(RuntimeError):
    """A registered checker failed without exposing its exception message."""


class ActionVerifier:
    """Verifies whether an action completed successfully."""

    def __init__(self, registry: "ActionRegistry | None" = None) -> None:
        self.registry = registry

    def verify(
        self,
        action_result: ActionResult,
        *,
        context: "AgentContext | None" = None,
        parameters: dict | None = None,
    ) -> VerificationResult:
        verified = action_result.success is True
        if self.registry is not None:
            definition = self.registry.get(action_result.action_name)
            try:
                verified = bool(
                    verified
                    and context is not None
                    and action_result.tool_name == definition.tool_name
                    and definition.verify(action_result, context, parameters or {})
                    is True
                )
            except Exception as exc:
                raise ActionVerificationError("Action verification failed.") from exc
        return VerificationResult(
            action_name=action_result.action_name,
            verified=verified,
            details=(
                "Action completed successfully."
                if verified
                else "Action execution failed."
                if self.registry is None
                else "Action verification failed."
            ),
        )
