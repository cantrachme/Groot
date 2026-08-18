from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AgentContext:
    """Execution context supplied to an agent."""

    user_id: UUID
    organization_id: UUID
    request_id: UUID
    task: str
    state: dict[str, Any] = field(default_factory=dict)
    permissions: frozenset[str] = frozenset()
