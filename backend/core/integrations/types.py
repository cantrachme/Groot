from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ConnectorResult:
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class NormalizedEvent:
    event_type: str
    title: str
    external_id: str | None = None
    description: str = ""
    source: str = ""
    occurred_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
