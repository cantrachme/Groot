import unittest

from ai_engine.app.db.database import Base
from ai_engine.app.models import DocumentChunkEmbedding


class DocumentChunkEmbeddingModelTests(unittest.TestCase):
    def test_model_is_registered_with_base_metadata(self):
        self.assertIn(
            "document_chunk_embeddings",
            Base.metadata.tables,
        )

    def test_embedding_column_uses_vector_type(self):
        table = DocumentChunkEmbedding.__table__
        column = table.c.embedding

        self.assertEqual(
            column.type.__class__.__name__,
            "VECTOR",
        )

    def test_document_chunk_and_model_are_unique(self):
        table = DocumentChunkEmbedding.__table__

        constraints = [
            constraint
            for constraint in table.constraints
            if constraint.name
            == "document_chunk_embedding_model_uq"
        ]

        self.assertEqual(len(constraints), 1)

        constraint = constraints[0]

        self.assertEqual(
            {
                column.name
                for column in constraint.columns
            },
            {
                "document_chunk_id",
                "model",
            },
        )


if __name__ == "__main__":
    unittest.main()
