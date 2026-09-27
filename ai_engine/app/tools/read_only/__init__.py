"""Build a private registry; these tools are never globally registered."""

from collections.abc import Callable

from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ...agents.agent import Agent
from ...agents.context import AgentContext
from ...db.database import SessionLocal
from .base import ReadOnlyToolRegistry
from .documents import ListDocumentsTool, ReadDocumentChunksTool


def build_read_only_registry(
    *,
    credentials: HTTPAuthorizationCredentials | None,
    agent: Agent,
    context: AgentContext,
    session_factory: Callable[[], Session] = SessionLocal,
) -> ReadOnlyToolRegistry:
    registry = ReadOnlyToolRegistry()
    for tool_type in (ListDocumentsTool, ReadDocumentChunksTool):
        registry.register(
            tool_type(
                credentials=credentials,
                agent=agent,
                context=context,
                session_factory=session_factory,
            )
        )
    return registry
