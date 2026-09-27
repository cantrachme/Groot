from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db.database import Base

# Reference-only metadata: Django still owns and migrates this table.
django_chunks = Table("core_documentchunk", MetaData(), Column("id", BigInteger))


class DocumentChunkEmbedding(Base):
    """Stores the vector representation of a Django DocumentChunk."""

    __tablename__ = "document_chunk_embeddings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    document_chunk_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(django_chunks.c.id, name="embedding_chunk_fk", ondelete="CASCADE"),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    dimensions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "document_chunk_id",
            "model",
            name="document_chunk_embedding_model_uq",
        ),
    )
