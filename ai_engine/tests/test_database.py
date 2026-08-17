import unittest
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from ai_engine.app.db.database import Base, SessionLocal, engine
from ai_engine.app.db.dependencies import get_db


class DatabaseInfrastructureTests(unittest.TestCase):
    def test_session_factory_is_bound_to_engine(self) -> None:
        session = SessionLocal()
        try:
            self.assertIs(session.get_bind(), engine)
        finally:
            session.close()

    def test_base_metadata_contains_rag_tables(self) -> None:
        self.assertIn(
            "document_chunk_embeddings",
            Base.metadata.tables,
        )

    def test_get_db_yields_and_closes_session(self) -> None:
        session = Mock(spec=Session)

        with patch("ai_engine.app.db.dependencies.SessionLocal", return_value=session):
            dependency = get_db()
            self.assertIs(next(dependency), session)
            dependency.close()

        session.close.assert_called_once_with()
