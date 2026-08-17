from io import BytesIO

from pypdf import PdfReader

from .base import DocumentExtractor


class PdfExtractor(DocumentExtractor):
    """Extracts text from PDF documents."""

    name = "pdf"

    supported_mime_types = (
        "application/pdf",
    )

    def extract(self, content: bytes) -> str:
        reader = PdfReader(BytesIO(content))

        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        return "\n".join(pages)
