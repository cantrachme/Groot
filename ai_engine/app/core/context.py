from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AIRequestContext:
    user_id: int | UUID
    organization_id: int | UUID
    request_id: UUID
