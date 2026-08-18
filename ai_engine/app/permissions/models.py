from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Permission:
    """A permission to perform an action on a resource."""

    resource: str
    action: str

    @property
    def name(self) -> str:
        return f"{self.resource}.{self.action}"


@dataclass(frozen=True)
class Role:
    """A named collection of permissions."""

    name: str
    permissions: tuple[Permission, ...] = ()


@dataclass(frozen=True)
class AuthorizationContext:
    """Authorization data for a user within an organization."""

    user_id: UUID
    organization_id: UUID
    roles: tuple[Role, ...]
    agent_name: str
