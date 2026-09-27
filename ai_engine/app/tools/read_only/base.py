"""Server-bound reads using the existing credential and agent permission checks."""

from collections.abc import Callable

from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, bindparam, text
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnClause

from ...agents.agent import Agent
from ...agents.capabilities import ToolPermission
from ...agents.context import AgentContext
from ...agents.policy import AgentCapabilityPolicy
from ...core.authentication import authenticate_knowledge
from ...db.database import SessionLocal
from ...permissions.engine import PermissionEngine
from ...permissions.models import AuthorizationContext, Permission, Role
from ..registry import ToolRegistry
from ..tool import Tool

KNOWLEDGE_READ = Permission(resource="knowledge", action="read")


class ReadParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    limit: int = Field(default=20, ge=1, le=100)


class ReadOnlyTool(Tool):
    """Trusted declarations supply a projection; this executor owns access and scope.

    Construct per request with server-held credentials/context. Definitions are
    trusted Python, never user-provided SQL or callbacks. Each read uses a fresh
    PostgreSQL transaction so it cannot flush a caller's pending writes.
    """

    parameters_model: type[ReadParameters]
    permission: Permission
    statement: Select
    tenant_column: ColumnClause
    cursor_field: str

    def __init__(
        self,
        *,
        credentials: HTTPAuthorizationCredentials | None,
        agent: Agent,
        context: AgentContext,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        self._credentials = credentials
        self._agent = agent
        self._context = context
        self._session_factory = session_factory

    def validate_definition(self) -> None:
        if type(self).execute is not ReadOnlyTool.execute:
            raise ValueError("Read-only tools must use the guarded executor.")
        if self.permission != KNOWLEDGE_READ:
            raise ValueError("Only knowledge.read is currently supported.")
        if not isinstance(self.statement, Select):
            raise TypeError("Read-only tools require a SELECT statement.")
        if not issubclass(self.parameters_model, ReadParameters):
            raise TypeError("Read-only tools require bounded read parameters.")

    def execute(self, **kwargs) -> dict:
        self.validate_definition()
        parameters = self.parameters_model.model_validate(kwargs)
        with self._session_factory() as db:
            try:
                # Must precede authentication and all application queries.
                db.execute(text("SET TRANSACTION READ ONLY"))
                identity = authenticate_knowledge(self._credentials, db)
                context = self._context
                if (
                    type(context.user_id) is not int
                    or type(context.organization_id) is not int
                    or context.user_id != identity.user_id
                    or context.organization_id != identity.organization_id
                ):
                    raise PermissionError("Tool context does not match membership.")
                grants = (
                    (KNOWLEDGE_READ,) if identity.role in {"admin", "member"} else ()
                )
                PermissionEngine().authorize(
                    AuthorizationContext(
                        user_id=identity.user_id,
                        organization_id=identity.organization_id,
                        roles=(Role(name=identity.role, permissions=grants),),
                        agent_name=self._agent.name,
                    ),
                    self.permission,
                )
                AgentCapabilityPolicy(
                    (ToolPermission(self.name, self.permission.name),),
                ).authorize(self._agent, self.name, context)
                query = self.statement.where(
                    self.tenant_column == bindparam("_organization_id"),
                ).limit(bindparam("_fetch_limit"))
                rows = (
                    db.execute(
                        query,
                        {
                            **parameters.model_dump(),
                            "_organization_id": identity.organization_id,
                            "_fetch_limit": parameters.limit + 1,
                        },
                    )
                    .mappings()
                    .all()
                )
                items = [dict(row) for row in rows[: parameters.limit]]
                return {
                    "items": items,
                    "next_cursor": (
                        items[-1][self.cursor_field]
                        if len(rows) > parameters.limit
                        else None
                    ),
                }
            finally:
                db.rollback()


class ReadOnlyToolRegistry(ToolRegistry):
    """Explicit, request-local discovery of guarded read tools only."""

    def register(self, tool: Tool) -> None:
        if not isinstance(tool, ReadOnlyTool):
            raise TypeError("Only read-only tool definitions can be registered.")
        tool.validate_definition()
        super().register(tool)
