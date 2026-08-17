from abc import ABC, abstractmethod
from typing import Any

from .types import ConnectorResult, NormalizedEvent


class IntegrationConnector(ABC):
    """Provider-independent contract for external integrations."""

    provider: str

    @abstractmethod
    def connect(self) -> ConnectorResult:
        """Establish or validate the provider connection."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> ConnectorResult:
        """Disconnect or revoke the provider connection."""
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> ConnectorResult:
        """Verify that the provider connection is usable."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, **kwargs: Any) -> ConnectorResult:
        """Fetch raw data from the external provider."""
        raise NotImplementedError

    @abstractmethod
    def normalize(
        self,
        data: list[dict[str, Any]],
    ) -> list[NormalizedEvent]:
        """Convert provider data into GROOT's normalized event format."""
        raise NotImplementedError
