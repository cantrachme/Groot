from sqlalchemy import text
from sqlalchemy.orm import Session

from .tenant_scope import tenant_options


class RAGDocumentService:
    """Loads Django DocumentChunk text for retrieved chunk IDs."""

    def get_chunk_texts(
        self,
        db: Session,
        chunk_ids: list[int],
        organization_id: int | None = None,
    ) -> dict[int, str]:
        scope = tenant_options(organization_id)
        if not chunk_ids or not scope:
            return {}

        statement = text(
            """
            SELECT c.id, c.text
            FROM core_documentchunk c
            JOIN core_document d ON d.id = c.document_id
            WHERE c.id = ANY(:chunk_ids) AND d.organization_id = :organization_id
              AND d.status = 'ready' AND d.embedding_status = 'ready'
            """
        )

        rows = db.execute(
            statement,
            {"chunk_ids": chunk_ids, **scope},
        ).all()

        return {
            int(row.id): row.text
            for row in rows
        }
