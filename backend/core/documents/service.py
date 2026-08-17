from django.utils import timezone

from core.models import Document, DocumentContent

from .registry import DocumentExtractorRegistry


class DocumentProcessingService:
    """Extracts document text and persists processing state."""

    def __init__(
        self,
        registry: DocumentExtractorRegistry,
    ) -> None:
        self.registry = registry

    def process(
        self,
        document: Document,
        content: bytes,
    ) -> DocumentContent:
        document_content, _ = DocumentContent.objects.get_or_create(
            document=document,
        )

        document_content.status = DocumentContent.Status.PROCESSING
        document_content.error = ""
        document_content.save(
            update_fields=[
                "status",
                "error",
                "updated_at",
            ]
        )

        try:
            extractor = self.registry.get(document.mime_type)
            text = extractor.extract(content)
        except (KeyError, UnicodeDecodeError, ValueError, TypeError) as exc:
            document_content.status = DocumentContent.Status.FAILED
            document_content.error = str(exc)
            document_content.extracted_at = None
            document_content.save(
                update_fields=[
                    "status",
                    "error",
                    "extracted_at",
                    "updated_at",
                ]
            )
            return document_content

        document_content.text = text
        document_content.status = DocumentContent.Status.READY
        document_content.extractor = extractor.name
        document_content.error = ""
        document_content.extracted_at = timezone.now()
        document_content.save(
            update_fields=[
                "text",
                "status",
                "extractor",
                "error",
                "extracted_at",
                "updated_at",
            ]
        )

        return document_content
