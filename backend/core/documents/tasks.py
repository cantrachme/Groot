from celery import shared_task


@shared_task
def process_document(
    document_id: int,
    content: bytes,
) -> dict:
    from core.documents import (
        DocumentChunkPersistenceService,
        DocumentExtractorRegistry,
        DocumentIntelligencePipeline,
        DocumentProcessingService,
        DocumentTextChunker,
        DocumentTextNormalizer,
        PlainTextExtractor,
    )
    from core.models import Document

    document = Document.objects.get(pk=document_id)

    registry = DocumentExtractorRegistry(
        [PlainTextExtractor()],
    )

    pipeline = DocumentIntelligencePipeline(
        processing_service=DocumentProcessingService(
            registry,
        ),
        normalizer=DocumentTextNormalizer(),
        chunker=DocumentTextChunker(),
        chunk_persistence=DocumentChunkPersistenceService(),
    )

    document_content = pipeline.process(
        document,
        content,
    )

    return {
        "success": (
            document_content.status
            == document_content.Status.READY
        ),
        "document_id": document.id,
        "status": document_content.status,
        "chunk_count": document.chunks.count(),
        "error": document_content.error or None,
    }
