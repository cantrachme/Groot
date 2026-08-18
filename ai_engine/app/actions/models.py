from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActionRequest:
    """A request to execute an approved action."""

    action_name: str
    approved: bool
    tool_name: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ActionResult:
    """The result of an action execution."""

    action_name: str
    tool_name: str
    parameters: dict[str, Any]
    success: bool
