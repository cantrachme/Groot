from django.utils import timezone

from core.integrations.types import NormalizedEvent
from core.models import Event, Organization


class EventPersistenceService:
    """Persists normalized integration events into the core data model."""

    def persist(
        self,
        organization: Organization,
        normalized_event: NormalizedEvent,
    ) -> Event:
        occurred_at = (
            normalized_event.occurred_at
            or timezone.now()
        )

        if normalized_event.external_id:
            event, _ = Event.objects.update_or_create(
                organization=organization,
                source=normalized_event.source,
                external_id=normalized_event.external_id,
                defaults={
                    "event_type": normalized_event.event_type,
                    "title": normalized_event.title,
                    "description": normalized_event.description,
                    "occurred_at": occurred_at,
                    "metadata": normalized_event.metadata,
                },
            )

            return event

        return Event.objects.create(
            organization=organization,
            event_type=normalized_event.event_type,
            title=normalized_event.title,
            description=normalized_event.description,
            source=normalized_event.source,
            external_id=None,
            occurred_at=occurred_at,
            metadata=normalized_event.metadata,
        )

    def persist_many(
        self,
        organization: Organization,
        normalized_events: list[NormalizedEvent],
    ) -> list[Event]:
        return [
            self.persist(
                organization,
                normalized_event,
            )
            for normalized_event in normalized_events
        ]
