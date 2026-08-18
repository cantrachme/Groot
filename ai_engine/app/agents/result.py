from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentResult:
    """Standardized result returned by an agent."""

    success: bool
    agent_name: str
    summary: str
    data: Any = None
    confidence: float | None = None
    evidence: tuple[Any, ...] = ()
    tool_calls: tuple[dict[str, Any], ...] = ()
    errors: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
