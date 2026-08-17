from abc import ABC, abstractmethod
import os


class CredentialProvider(ABC):
    """Abstraction for retrieving integration credentials."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        raise NotImplementedError

    def has(self, key: str) -> bool:
        return self.get(key) is not None


class EnvironmentCredentialProvider(CredentialProvider):
    """Development credential provider backed by environment variables."""

    def get(self, key: str) -> str | None:
        value = os.getenv(key)

        if value is None:
            return None

        value = value.strip()
        return value or None
