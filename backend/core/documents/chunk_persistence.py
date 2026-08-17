from core.models import Document, DocumentChunk

from .chunker import TextChunk


class DocumentChunkPersistenceService:
    """Persists deterministic text chunks for a document."""

    def persist(
        self,
        document: Document,
        chunks: list[TextChunk],
    ) -> list[DocumentChunk]:
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
