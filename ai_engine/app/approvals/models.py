from dataclasses import dataclass
from enum import Enum


class ActionRisk(str, Enum):
    """Risk classification for controlled actions."""

    READ = "read"
    LOW = "low"
    HIGH_IMPACT = "high_impact"


@dataclass(frozen=True)
class ApprovalRequirement:
    """Approval requirement determined for an action."""

    action_name: str
    risk: ActionRisk
    approval_required: bool
