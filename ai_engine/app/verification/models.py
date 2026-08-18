from dataclasses import dataclass

from ai_engine.app.actions import ActionResult


@dataclass(frozen=True)
class VerificationResult:
    action_name: str
    verified: bool
    details: str
