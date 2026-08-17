from typing import Any

import requests

from ..base import IntegrationConnector
from ..types import ConnectorResult, NormalizedEvent


class GitHubConnector(IntegrationConnector):
    """Read-only GitHub integration connector."""

    provider = "github"
    api_base_url = "https://api.github.com"

    def __init__(self, token: str) -> None:
        if not token.strip():
            raise ValueError("GitHub token cannot be empty.")

        self.token = token

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def connect(self) -> ConnectorResult:
        return self.test_connection()

    def disconnect(self) -> ConnectorResult:
        return ConnectorResult(success=True)

    def test_connection(self) -> ConnectorResult:
        try:
            response = requests.get(
                f"{self.api_base_url}/user",
                headers=self._headers(),
                timeout=10,
            )
        except requests.RequestException as exc:
            return ConnectorResult(
                success=False,
                error=str(exc),
            )

        if response.ok:
            return ConnectorResult(
                success=True,
                data=[response.json()],
            )

        return ConnectorResult(
            success=False,
            error=f"GitHub API returned HTTP {response.status_code}.",
        )

    def fetch(self, **kwargs: Any) -> ConnectorResult:
        endpoint = kwargs.get("endpoint", "/user")

        try:
            response = requests.get(
                f"{self.api_base_url}{endpoint}",
                headers=self._headers(),
                timeout=10,
            )
        except requests.RequestException as exc:
            return ConnectorResult(
                success=False,
                error=str(exc),
            )

        if not response.ok:
            return ConnectorResult(
                success=False,
                error=f"GitHub API returned HTTP {response.status_code}.",
            )

        payload = response.json()

        if isinstance(payload, list):
            data = payload
        else:
            data = [payload]

        return ConnectorResult(
            success=True,
            data=data,
        )

    def normalize(
        self,
        data: list[dict[str, Any]],
    ) -> list[NormalizedEvent]:
        return []
