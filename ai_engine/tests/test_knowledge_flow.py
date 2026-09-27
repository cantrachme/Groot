import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from ai_engine.app.agents.context import AgentContext
from ai_engine.app.agents.knowledge import KnowledgeAgent
from ai_engine.app.core.authentication import KnowledgeIdentity, authenticate_knowledge
from ai_engine.app.core.context import AIRequestContext
from ai_engine.app.db.database import Base
from ai_engine.app.db.dependencies import get_db
from ai_engine.app.embeddings import EmbeddingConfig
from ai_engine.app.embeddings.factory import build_embedding_provider
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.main import app, get_knowledge_agent
from ai_engine.app.models import DocumentChunkEmbedding
from ai_engine.app.services.ai_service import AIService
from ai_engine.app.services.context_assembly_service import AssembledContext
from ai_engine.app.services.embedding_service import EmbeddingService
from ai_engine.app.services.rag_document_service import RAGDocumentService
from ai_engine.app.services.rag_service import RAGResponse, RAGService
from ai_engine.app.services.retrieval_service import RetrievalResult, RetrievalService
from ai_engine.app.services.similarity_search_service import SimilaritySearchService

CONFIG = EmbeddingConfig(provider="local", model="test", dimensions=3)


class KnowledgeAuthenticationTests(unittest.TestCase):
    def test_missing_token_never_queries_database(self):
        db = Mock()
        with self.assertRaises(HTTPException) as raised:
            authenticate_knowledge(None, db)
        self.assertEqual(raised.exception.status_code, 401)
        db.execute.assert_not_called()

    def test_token_is_hashed_and_identity_comes_from_membership(self):
        db = Mock()
        db.execute.return_value.first.return_value = SimpleNamespace(
            user_id=7,
            organization_id=12,
            role="member",
        )
        identity = authenticate_knowledge(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-secret"),
            db,
        )
        self.assertEqual(identity, KnowledgeIdentity(7, 12, "member"))
        statement, parameters = db.execute.call_args.args
        self.assertEqual(
            parameters, {"digest": hashlib.sha256(b"test-secret").hexdigest()}
        )
        self.assertNotIn("test-secret", str(statement))

    def test_unknown_token_is_rejected(self):
        db = Mock()
        db.execute.return_value.first.return_value = None
        with self.assertRaises(HTTPException) as raised:
            authenticate_knowledge(
                HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad"), db
            )
        self.assertEqual(raised.exception.status_code, 401)


class ScopedKnowledgeTests(unittest.TestCase):
    def test_no_scope_search_is_fail_closed(self):
        db = Mock()
        db.execute.return_value.all.return_value = []
        SimilaritySearchService().search(db, [1, 0, 0], "test", 3)
        self.assertIn("FALSE", str(db.execute.call_args.args[0]))

    def test_scope_precedes_ranking_and_limit(self):
        db = Mock()
        db.execute.return_value.all.return_value = []
        SimilaritySearchService().search(
            db, [1, 0, 0], "test", 3, top_k=1, organization_id=8
        )
        query = db.execute.call_args.args[0]
        self.assertIn("d.organization_id = :organization_id", str(query))
        self.assertLess(str(query).index("EXISTS"), str(query).index("LIMIT"))
        self.assertEqual(query.compile().params["organization_id"], 8)

    def test_invalid_scope_rejected(self):
        for organization in (True, 0, -1, "8", uuid4()):
            with self.subTest(organization=organization), self.assertRaises(ValueError):
                RAGDocumentService().get_chunk_texts(Mock(), [1], organization)

    def test_no_scope_text_lookup_never_queries_database(self):
        db = Mock()
        self.assertEqual(RAGDocumentService().get_chunk_texts(db, [1]), {})
        db.execute.assert_not_called()

    def test_retrieval_passes_integer_scope(self):
        search = Mock()
        search.search.return_value = []
        provider = Mock()
        provider.embed_text.return_value = [1, 0, 0]
        RetrievalService(provider, CONFIG, search).retrieve(
            Mock(), "question", organization_id=5
        )
        self.assertEqual(search.search.call_args.kwargs["organization_id"], 5)

    def test_scoped_answer_ignores_supplied_text_and_does_not_invent_empty_answer(self):
        retrieval = Mock()
        retrieval.retrieve.return_value = RetrievalResult("question", ())
        documents = Mock()
        documents.get_chunk_texts.return_value = {}
        llm = Mock()
        service = RAGService(
            llm, Mock(), CONFIG, retrieval_service=retrieval, document_service=documents
        )
        result = service.answer(
            Mock(), "question", chunk_texts={9: "injected"}, organization_id=7
        )
        self.assertEqual(result.context.items, ())
        self.assertIn("not enough document context", result.response.text)
        llm.generate.assert_not_called()
        self.assertEqual(
            documents.get_chunk_texts.call_args.kwargs["organization_id"], 7
        )

    def test_ai_service_uses_shared_answer_composition(self):
        service = AIService(llm_provider=Mock(), embedding_config=CONFIG)
        db = Mock()
        context = AIRequestContext(2, 3, uuid4())
        with patch("ai_engine.app.services.ai_service.RAGService") as rag:
            expected = rag.return_value.answer.return_value
            self.assertIs(
                service.handle_rag(context, db, "question", top_k=2), expected
            )
            rag.return_value.answer.assert_called_once_with(
                db=db,
                query="question",
                top_k=2,
                organization_id=3,
            )

    def test_integer_agent_identity_is_passed_to_rag(self):
        rag = Mock()
        rag.answer.return_value = RAGResponse(
            "q", AssembledContext((), ""), LLMResponse(text="empty", tool_calls=())
        )
        db = Mock(spec=Session)
        KnowledgeAgent(rag).execute(AgentContext(1, 2, uuid4(), "q", state={"db": db}))
        rag.answer.assert_called_once_with(db=db, query="q", top_k=5, organization_id=2)

    def test_django_reference_is_not_added_to_ai_metadata(self):
        self.assertNotIn("core_documentchunk", Base.metadata.tables)
        constraint = next(iter(DocumentChunkEmbedding.__table__.foreign_keys))
        self.assertEqual(constraint.ondelete, "CASCADE")


class KnowledgeHTTPTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock(spec=Session)
        self.agent = Mock()
        self.saved_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: self.db
        app.dependency_overrides[get_knowledge_agent] = lambda: self.agent
        self.client = TestClient(app)
        self.payload = {"request_id": str(uuid4()), "message": "Question"}

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.saved_overrides)

    def test_missing_token_denied_before_agent_execution(self):
        response = self.client.post("/rag", json=self.payload)
        self.assertEqual(response.status_code, 401)
        self.agent.execute.assert_not_called()

    def test_identity_fields_and_invalid_query_are_rejected(self):
        app.dependency_overrides[authenticate_knowledge] = lambda: KnowledgeIdentity(
            1, 2, "member"
        )
        for fields in (
            {"user_id": 9},
            {"organization_id": 7},
            {"message": "  "},
            {"top_k": 0},
            {"top_k": 51},
        ):
            with self.subTest(fields=fields):
                response = self.client.post("/rag", json={**self.payload, **fields})
                self.assertEqual(response.status_code, 422)
        self.agent.execute.assert_not_called()

    def test_evidence_and_server_identity_are_preserved(self):
        app.dependency_overrides[authenticate_knowledge] = lambda: KnowledgeIdentity(
            1, 2, "member"
        )
        self.agent.execute.return_value = SimpleNamespace(
            data={"query": "Question", "citations": (4,)},
            summary="Answer",
            metadata={"context": "Evidence"},
            evidence=({"document_chunk_id": 4, "text": "Evidence", "similarity": 1.0},),
        )
        response = self.client.post("/rag", json=self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["citations"], [4])
        self.assertEqual(response.json()["evidence"][0]["text"], "Evidence")
        context = self.agent.execute.call_args.args[0]
        self.assertEqual((context.user_id, context.organization_id), (1, 2))
        self.assertEqual(context.permissions, frozenset({"knowledge.read"}))


class EmbeddingUpsertTests(unittest.TestCase):
    def test_failure_rolls_back_transaction(self):
        provider = Mock()
        provider.embed_texts.return_value = [[1, 0, 0]]
        db = Mock()
        db.execute.side_effect = RuntimeError("write failed")
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            EmbeddingService(provider, CONFIG).upsert_chunks(db, [(1, "text")])
        db.rollback.assert_called_once()
        db.commit.assert_not_called()

    def test_all_batches_validate_before_writing(self):
        provider = Mock()
        provider.embed_texts.side_effect = [[[1, 0, 0]], [[1, 0]]]
        db = Mock()
        config = EmbeddingConfig("local", "test", 3, batch_size=1)
        with self.assertRaisesRegex(ValueError, "dimensions"):
            EmbeddingService(provider, config).upsert_chunks(
                db, [(1, "first"), (2, "second")]
            )
        db.execute.assert_not_called()
        db.commit.assert_not_called()

    def test_empty_upsert_does_no_work(self):
        db, provider = Mock(), Mock()
        self.assertEqual(EmbeddingService(provider, CONFIG).upsert_chunks(db, []), [])
        db.execute.assert_not_called()
        provider.embed_texts.assert_not_called()

    def test_shared_factory_honors_ollama_url(self):
        with patch.dict(
            "os.environ", {"OLLAMA_BASE_URL": "http://ollama.internal:11434"}
        ):
            provider = build_embedding_provider(EmbeddingConfig("ollama", "test", 3))
        self.assertEqual(provider.base_url, "http://ollama.internal:11434")
