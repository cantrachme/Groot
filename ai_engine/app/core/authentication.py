"""Read Django-owned credentials and current membership through the shared DB."""

import hashlib
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db.dependencies import get_db


@dataclass(frozen=True)
class KnowledgeIdentity:
    user_id: int
    organization_id: int
    role: str


bearer = HTTPBearer(auto_error=False)


def authenticate_knowledge(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> KnowledgeIdentity:
    if credentials is not None and credentials.scheme.lower() == "bearer":
        row = db.execute(
            text("""
            SELECT m.user_id, m.organization_id, m.role
            FROM core_knowledgeaccesstoken t
            JOIN core_membership m ON m.id = t.membership_id
            JOIN core_user u ON u.id = m.user_id
            WHERE t.digest = :digest AND t.expires_at > CURRENT_TIMESTAMP
              AND u.is_active = TRUE
        """),
            {"digest": hashlib.sha256(credentials.credentials.encode()).hexdigest()},
        ).first()
        if row is not None:
            return KnowledgeIdentity(row.user_id, row.organization_id, row.role)
    raise HTTPException(
        status_code=401,
        detail="A valid knowledge access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
