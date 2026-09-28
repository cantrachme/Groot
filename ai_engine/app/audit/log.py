import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from threading import RLock
from uuid import UUID

from .models import AuditEvent


class AuditLog:
    """Ordered audit events, optionally persisted to a local JSON-lines journal.

    A journal belongs to one application process. Corrupt/truncated records fail
    closed on load. No action inputs, provider outputs or credentials are stored.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._events: list[AuditEvent] = []
        self._path = Path(path) if path is not None else None
        self._lock = RLock()
        if self._path is not None and self._path.exists():
            for line in self._path.read_text().splitlines():
                data = json.loads(line)
                for key in (
                    "user_id",
                    "organization_id",
                    "actor_user_id",
                    "operation_id",
                    "request_id",
                ):
                    if isinstance(data.get(key), str):
                        data[key] = UUID(data[key])
                data["occurred_at"] = datetime.fromisoformat(data["occurred_at"])
                self._events.append(AuditEvent(**data))

    @property
    def durable(self) -> bool:
        return self._path is not None

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def record(self, event: AuditEvent) -> None:
        with self._lock:
            if self._path is not None:
                encoded = json.dumps(asdict(event), default=str) + "\n"
                # A restrictive creation mode; parents must be provisioned by the host.
                descriptor = os.open(
                    self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
                )
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    output.write(encoded)
                    output.flush()
                    os.fsync(output.fileno())
            self._events.append(event)
