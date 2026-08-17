from dataclasses import dataclass
from typing import Any

from core.integrations.service import IntegrationService
from core.integrations.types import NormalizedEvent


@dataclass(frozen=True)
class IngestionResult:
    success: bool
    events: list[NormalizedEvent]
    error: str | None = None


class IngestionService:
    """Coordinates external data retrieval and normalization."""

    def __init__(
        self,
        integration_service: IntegrationService,
    ) -> None:
        self.integration_service = integration_service

    def ingest(
        self,
        provider: str,
        credential_key: str,
        **kwargs: Any,
    ) -> IngestionResult:
        result, events = (
            self.integration_service.fetch_and_normalize(
                provider,
                credential_key,
                **kwargs,
            )
        )

        if not result.success:
            return IngestionResult(
                success=False,
                events=[],
                error=result.error,
            )

        return IngestionResult(
            success=True,
            events=events,
        )
