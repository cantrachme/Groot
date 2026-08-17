from .base import IntegrationConnector


class IntegrationRegistry:
    """Registry of available external integration connectors."""

    def __init__(self) -> None:
        self._connectors: dict[str, IntegrationConnector] = {}

    def register(self, connector: IntegrationConnector) -> None:
        provider = connector.provider

        if provider in self._connectors:
            raise ValueError(
                f"Integration connector already registered: {provider}"
            )

        self._connectors[provider] = connector

    def get(self, provider: str) -> IntegrationConnector:
        try:
            return self._connectors[provider]
        except KeyError as exc:
            raise KeyError(
                f"No integration connector registered for: {provider}"
            ) from exc

    def has(self, provider: str) -> bool:
        return provider in self._connectors

    def providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._connectors))
