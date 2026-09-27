"""Bounded projections of ready Django-owned knowledge, without ORM ownership."""

from pydantic import Field
from sqlalchemy import bindparam, column, func, select, table

from .base import KNOWLEDGE_READ, ReadOnlyTool, ReadParameters

# Lightweight query tables deliberately do not join Alembic's Base.metadata.
documents = table(
    "core_document",
    *(
        column(name)
        for name in (
            "id",
            "organization_id",
            "name",
            "document_type",
            "mime_type",
            "size",
            "status",
            "embedding_status",
        )
    ),
)
chunks = table(
    "core_documentchunk",
    *(
        column(name)
        for name in (
            "id",
            "document_id",
            "chunk_index",
            "text",
        )
    ),
)
ready = (
    documents.c.status == "ready",
    documents.c.embedding_status == "ready",
)


class ListDocumentsParameters(ReadParameters):
    after_id: int = Field(default=0, ge=0, le=9223372036854775807)


class ReadChunksParameters(ReadParameters):
    document_id: int = Field(ge=1, le=9223372036854775807)
    after_index: int = Field(default=-1, ge=-1, le=2147483647)
    limit: int = Field(default=5, ge=1, le=20)


class ListDocumentsTool(ReadOnlyTool):
    name = "list_documents"
    description = "List ready knowledge documents in your organization by ID."
    parameters_model = ListDocumentsParameters
    permission = KNOWLEDGE_READ
    tenant_column = documents.c.organization_id
    cursor_field = "id"
    statement = (
        select(
            documents.c.id,
            documents.c.name,
            documents.c.document_type,
            documents.c.mime_type,
            documents.c.size,
        )
        .where(
            *ready,
            documents.c.id > bindparam("after_id"),
        )
        .order_by(documents.c.id)
    )


class ReadDocumentChunksTool(ReadOnlyTool):
    name = "read_document_chunks"
    description = (
        "Read ready document chunks in your organization by chunk index. "
        "Each text is capped at 4000 characters; truncated marks longer chunks."
    )
    parameters_model = ReadChunksParameters
    permission = KNOWLEDGE_READ
    tenant_column = documents.c.organization_id
    cursor_field = "chunk_index"
    statement = (
        select(
            chunks.c.id.label("document_chunk_id"),
            chunks.c.document_id,
            chunks.c.chunk_index,
            func.left(chunks.c.text, 4000).label("text"),
            (func.char_length(chunks.c.text) > 4000).label("truncated"),
        )
        .select_from(
            chunks.join(documents, chunks.c.document_id == documents.c.id),
        )
        .where(
            *ready,
            documents.c.id == bindparam("document_id"),
            chunks.c.chunk_index > bindparam("after_index"),
        )
        .order_by(chunks.c.chunk_index)
    )
