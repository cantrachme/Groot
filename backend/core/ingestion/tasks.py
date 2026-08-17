from celery import shared_task


@shared_task
def ingest_integration(
    provider: str,
    credential_key: str,
    organization_id: int,
    **kwargs,
) -> dict:
    from core.ingestion import (
        EventPersistenceService,
        IngestionService,
    )
    from core.integrations import (
        EnvironmentCredentialProvider,
        IntegrationService,
        build_integration_registry,
    )
    from core.models import Organization

    credentials = EnvironmentCredentialProvider()

    registry = build_integration_registry(
        credentials,
    )

    integration_service = IntegrationService(
        registry=registry,
        credentials=credentials,
    )

    ingestion_service = IngestionService(
        integration_service=integration_service,
    )

    organization = Organization.objects.get(
        pk=organization_id,
    )

    result = ingestion_service.ingest(
        provider,
        credential_key,
        **kwargs,
    )

    if not result.success:
        return {
            "success": False,
            "event_count": 0,
            "persisted_count": 0,
            "error": result.error,
        }

    persistence = EventPersistenceService()

    persisted_events = persistence.persist_many(
        organization,
        result.events,
    )

    return {
        "success": True,
        "event_count": len(result.events),
        "persisted_count": len(persisted_events),
        "error": None,
    }
