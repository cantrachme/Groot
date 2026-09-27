from functools import partial

from django.db import transaction

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

    @transaction.atomic
    def process(
        self,
        document: Document,
        content: bytes,
    ) -> DocumentContent:
        Document.objects.select_for_update().get(pk=document.pk)
        document.embedding_status = Document.Status.PENDING
        document.embedding_error = ""
        document.status = Document.Status.PROCESSING
        document.save(
            update_fields=[
                "status",
                "embedding_status",
                "embedding_error",
                "updated_at",
            ],
        )

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

            document.status = Document.Status.FAILED
            document.embedding_status = Document.Status.FAILED
            document.save(
                update_fields=[
                    "status",
                    "embedding_status",
                    "updated_at",
                ],
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

        document.status = Document.Status.READY
        document.save(
            update_fields=[
                "status",
                "updated_at",
            ],
        )

        from .tasks import enqueue_document_embeddings
        transaction.on_commit(partial(enqueue_document_embeddings, document.pk))
        return document_content
