from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class AuditEvent:
    """A record of an action performed within an organization."""

    event_name: str
    user_id: int | UUID
    organization_id: int | UUID
    agent_name: str
    operation_id: UUID | None = None
    request_id: UUID | None = None
    action_name: str | None = None
    tool_name: str | None = None
    risk: str | None = None
    error_type: str | None = None
    actor_user_id: int | UUID | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
