from .models import AuditEvent


class AuditLog:
    """Stores audit events in execution order."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def record(self, event: AuditEvent) -> None:
        self._events.append(event)
