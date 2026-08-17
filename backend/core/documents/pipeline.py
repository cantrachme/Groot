from core.models import Document, DocumentContent

from .chunk_persistence import DocumentChunkPersistenceService
from .chunker import DocumentTextChunker
from .normalizer import DocumentTextNormalizer
from .service import DocumentProcessingService


class DocumentIntelligencePipeline:
    """Runs extraction, normalization, and chunk persistence."""

    def __init__(
        self,
        processing_service: DocumentProcessingService,
        normalizer: DocumentTextNormalizer,
        chunker: DocumentTextChunker,
        chunk_persistence: DocumentChunkPersistenceService,
    ) -> None:
        self.processing_service = processing_service
        self.normalizer = normalizer
        self.chunker = chunker
        self.chunk_persistence = chunk_persistence

    def process(
        self,
        document: Document,
        content: bytes,
    ) -> DocumentContent:
        document_content = self.processing_service.process(
            document,
            content,
        )

        if (
            document_content.status
            != DocumentContent.Status.READY
        ):
            self.chunk_persistence.persist(
                document,
                [],
            )
            return document_content

        normalized_text = self.normalizer.normalize(
            document_content.text,
        )

        document_content.text = normalized_text
        document_content.save(
            update_fields=[
                "text",
                "updated_at",
            ],
        )

        chunks = self.chunker.chunk(
            normalized_text,
        )

        self.chunk_persistence.persist(
            document,
            chunks,
        )

        return document_content
