"""Trusted, provider-independent action definitions. No actions register by default."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from ..approvals.models import ActionRisk
from ..permissions.models import Permission
from .models import ActionRequest, ActionResult

if TYPE_CHECKING:
    from ..agents.context import AgentContext


class ActionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    tool_name: str
    permission: Permission
    risk: ActionRisk
    parameters_model: type[ActionParameters]
    execute: Callable[[ActionRequest, "AgentContext"], bool]
    verify: Callable[[ActionResult, "AgentContext", dict], bool]


class ActionRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}

    def register(self, definition: ActionDefinition) -> None:
        if any(
            not re.fullmatch(r"[a-z][a-z0-9_.-]{0,79}", name)
            for name in (
                definition.name,
                definition.tool_name,
                definition.permission.resource,
                definition.permission.action,
            )
        ):
            raise ValueError("Invalid action definition name.")
        if not isinstance(definition.risk, ActionRisk):
            raise TypeError("Action risk must be a trusted ActionRisk.")
        if not issubclass(definition.parameters_model, ActionParameters) or (
            definition.parameters_model.model_config.get("extra") != "forbid"
            or definition.parameters_model.model_config.get("strict") is not True
        ):
            raise ValueError(
                "Action parameters must be strict and reject extra fields."
            )
        if not callable(definition.execute) or not callable(definition.verify):
            raise TypeError(
                "Actions require execution and independent verification callbacks."
            )
        if definition.name in self._actions:
            raise ValueError("Action already registered.")
        self._actions[definition.name] = definition

    def get(self, name: str) -> ActionDefinition:
        return self._actions[name]
