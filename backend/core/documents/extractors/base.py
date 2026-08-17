from abc import ABC, abstractmethod


class DocumentExtractor(ABC):
    """Provider-independent interface for document text extraction."""

    name: str

    @property
    @abstractmethod
    def supported_mime_types(self) -> tuple[str, ...]:
        raise NotImplementedError

    @abstractmethod
    def extract(self, content: bytes) -> str:
        raise NotImplementedError
