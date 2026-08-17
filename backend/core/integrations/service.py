from typing import Any

from .base import IntegrationConnector
from .credentials import CredentialProvider
from .registry import IntegrationRegistry
from .types import ConnectorResult, NormalizedEvent


class IntegrationService:
    """Coordinates registered connectors and their credentials."""

    def __init__(
        self,
        registry: IntegrationRegistry,
        credentials: CredentialProvider,
    ) -> None:
        self.registry = registry
        self.credentials = credentials

    def get_connector(
        self,
        provider: str,
    ) -> IntegrationConnector:
        return self.registry.get(provider)

    def test_connection(
        self,
        provider: str,
        credential_key: str,
    ) -> ConnectorResult:
        token = self.credentials.get(credential_key)

        if not token:
            return ConnectorResult(
                success=False,
                error=f"Credential not configured: {credential_key}",
            )

        connector = self.get_connector(provider)

        return connector.test_connection()

    def fetch(
        self,
        provider: str,
        credential_key: str,
        **kwargs: Any,
    ) -> ConnectorResult:
        token = self.credentials.get(credential_key)

        if not token:
            return ConnectorResult(
                success=False,
                error=f"Credential not configured: {credential_key}",
            )

        connector = self.get_connector(provider)

        return connector.fetch(**kwargs)

    def fetch_and_normalize(
        self,
        provider: str,
        credential_key: str,
        **kwargs: Any,
    ) -> tuple[ConnectorResult, list[NormalizedEvent]]:
        result = self.fetch(
            provider,
            credential_key,
            **kwargs,
        )

        if not result.success:
            return result, []

        connector = self.get_connector(provider)

        events = connector.normalize(result.data)

        return result, events
