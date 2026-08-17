from sqlalchemy import text
from sqlalchemy.orm import Session


class RAGDocumentService:
    """Loads Django DocumentChunk text for retrieved chunk IDs."""

    def get_chunk_texts(
        self,
        db: Session,
        chunk_ids: list[int],
    ) -> dict[int, str]:
        if not chunk_ids:
            return {}

        statement = text(
            """
            SELECT id, text
            FROM core_documentchunk
            WHERE id = ANY(:chunk_ids)
            """
        )

        rows = db.execute(
            statement,
            {"chunk_ids": chunk_ids},
        ).all()

        return {
            int(row.id): row.text
            for row in rows
        }
