from .base import DocumentExtractor


class PlainTextExtractor(DocumentExtractor):
    """Extracts UTF-8 text documents."""

    name = "plain_text"

    @property
    def supported_mime_types(self) -> tuple[str, ...]:
        return (
            "text/plain",
            "text/markdown",
            "text/csv",
        )

    def extract(self, content: bytes) -> str:
        return content.decode("utf-8")
