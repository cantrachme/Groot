from django.db import transaction

from core.models import Document, DocumentChunk

from .chunker import TextChunk


class DocumentChunkPersistenceService:
    """Persists deterministic text chunks for a document."""

    @transaction.atomic
    def persist(
        self,
        document: Document,
        chunks: list[TextChunk],
    ) -> list[DocumentChunk]:
        Document.objects.select_for_update().get(pk=document.pk)
        Document.objects.filter(pk=document.pk).update(
            embedding_status=Document.Status.PENDING, embedding_error="",
        )
        DocumentChunk.objects.filter(
            document=document,
        ).delete()

        return [
            DocumentChunk.objects.create(
                document=document,
                chunk_index=chunk.index,
                text=chunk.text,
                character_count=chunk.character_count,
            )
            for chunk in chunks
        ]
