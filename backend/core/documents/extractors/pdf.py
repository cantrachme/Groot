from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .base import DocumentExtractor


class PdfExtractor(DocumentExtractor):
    """Extracts text from PDF documents."""

    name = "pdf"

    supported_mime_types = (
        "application/pdf",
    )

    def extract(self, content: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(content))

            pages: list[str] = []

            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)

            return "\n".join(pages)
        except PdfReadError as exc:
            raise ValueError(
                f"Unable to read PDF document: {exc}"
            ) from exc
