"""Remove legacy orphans and cascade embedding deletion with Django chunks.

Revision ID: b17d32a0e901
Revises: a66f2147d28c
"""

from alembic import op

revision = "b17d32a0e901"
down_revision = "a66f2147d28c"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DELETE FROM document_chunk_embeddings e
        WHERE NOT EXISTS (SELECT 1 FROM core_documentchunk c WHERE c.id = e.document_chunk_id)
    """)
    op.create_foreign_key(
        "embedding_chunk_fk",
        "document_chunk_embeddings",
        "core_documentchunk",
        ["document_chunk_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "embedding_chunk_fk", "document_chunk_embeddings", type_="foreignkey"
    )
