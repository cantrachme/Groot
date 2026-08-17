from .credentials import CredentialProvider
from .providers.github import GitHubConnector
from .registry import IntegrationRegistry


def build_integration_registry(
    credentials: CredentialProvider,
) -> IntegrationRegistry:
    registry = IntegrationRegistry()

    github_token = credentials.get("GITHUB_TOKEN")

    if github_token:
        registry.register(
            GitHubConnector(github_token)
        )

    return registry
