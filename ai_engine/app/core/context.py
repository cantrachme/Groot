from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AIRequestContext:
    user_id: UUID
    organization_id: UUID
    request_id: UUID
