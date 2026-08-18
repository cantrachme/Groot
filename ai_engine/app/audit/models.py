from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuditEvent:
    """A record of an action performed within an organization."""

    event_name: str
    user_id: UUID
    organization_id: UUID
    agent_name: str
