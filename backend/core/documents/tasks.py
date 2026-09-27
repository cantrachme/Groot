from celery import shared_task
from django.db import transaction
from kombu.exceptions import OperationalError as BrokerError
from sqlalchemy.exc import SQLAlchemyError


def persist_document_embeddings(chunks):
    from ai_engine.app.db.database import SessionLocal
    from ai_engine.app.embeddings import EmbeddingConfig
    from ai_engine.app.embeddings.factory import build_embedding_provider
    from ai_engine.app.services.chunk_embedding_service import (
        DocumentChunkEmbeddingService,
        DocumentChunkInput,
    )

    config = EmbeddingConfig.from_env()
    service = DocumentChunkEmbeddingService(build_embedding_provider(config), config)
    with SessionLocal() as db:
        service.upsert_chunks(db, [DocumentChunkInput(pk, text) for pk, text in chunks])


def enqueue_document_embeddings(document_id):
    from core.models import Document

    try:
        embed_document.delay(document_id)
    except BrokerError:
        Document.objects.filter(pk=document_id).update(
            embedding_status=Document.Status.FAILED,
            embedding_error="Embedding dispatch failed; retry embed_document after broker recovery.",
        )


@shared_task(autoretry_for=(RuntimeError, SQLAlchemyError), retry_backoff=True,
             retry_kwargs={"max_retries": 3})
def embed_document(document_id: int) -> dict:
    from core.models import Document

    error = None
    with transaction.atomic():
        document = Document.objects.select_for_update().filter(pk=document_id).first()
        if document is None or document.status != Document.Status.READY:
            return {"success": False, "document_id": document_id, "error": "Document is not ready."}
        chunks = list(document.chunks.order_by("chunk_index").values_list("id", "text"))
        try:
            # Hold the document lock through the AI transaction. Reprocessing uses
            # the same lock, so old jobs cannot attach vectors to replaced chunks.
            persist_document_embeddings(chunks)
        except (RuntimeError, SQLAlchemyError, ValueError, TypeError) as exc:
            document.embedding_status = Document.Status.FAILED
            document.embedding_error = "Embedding failed; retry embed_document after resolving the provider/database error."
            error = exc
        else:
            document.embedding_status = Document.Status.READY
            document.embedding_error = ""
        document.save(update_fields=["embedding_status", "embedding_error", "updated_at"])
    if error is not None:
        raise error
    return {"success": True, "document_id": document_id, "chunk_count": len(chunks)}


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
        PdfExtractor,
        PlainTextExtractor,
    )
    from core.models import Document

    document = Document.objects.get(pk=document_id)

    registry = DocumentExtractorRegistry(
        [
            PlainTextExtractor(),
            PdfExtractor(),
        ],
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
