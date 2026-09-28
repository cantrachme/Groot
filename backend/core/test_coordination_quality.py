"""Coordinate real tenant-scoped reads; only external embedding/LLM providers are fake."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import URL, create_engine, text
from sqlalchemy.orm import sessionmaker

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentRegistry,
    AgentResult,
    AgentSelection,
    AgentSupervisor,
    KnowledgeAgent,
    MultiAgentCoordinator,
)
from ai_engine.app.core.authentication import authenticate_knowledge
from ai_engine.app.embeddings import EmbeddingConfig, EmbeddingProvider
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.services.chunk_embedding_service import (
    DocumentChunkEmbeddingService,
    DocumentChunkInput,
)
from ai_engine.app.services.rag_service import RAGService
from ai_engine.app.tools.read_only import build_read_only_registry

from .knowledge_tokens import issue_knowledge_token
from .models import (
    Document,
    DocumentChunk,
    KnowledgeAccessToken,
    Membership,
    Organization,
    User,
)


class ReadAgent(Agent):
    description = "Trusted test agent using the existing guarded read registry"
    capabilities = ("read",)
    allowed_tools = ("read_document_chunks",)

    def __init__(self, name, credentials, sessions, document_id, arguments=None):
        self.name = name
        self.credentials = credentials
        self.sessions = sessions
        self.arguments = {"document_id": document_id, **(arguments or {})}
        self.contexts = []

    def execute(self, context):
        self.contexts.append(context)
        registry = build_read_only_registry(
            credentials=self.credentials,
            agent=self,
            context=context,
            session_factory=self.sessions,
        )
        page = registry.get("read_document_chunks").execute(**self.arguments)
        return AgentResult(
            success=True,
            agent_name=self.name,
            summary="\n".join(item["text"] for item in page["items"]),
            evidence=tuple(page["items"]),
            data={
                "citations": tuple(item["document_chunk_id"] for item in page["items"])
            },
        )


class CoordinationQualityPostgresTests(TransactionTestCase):
    def setUp(self):
        db = connection.settings_dict
        self.assertTrue(str(db["NAME"]).startswith("test_"))
        self.engine = create_engine(
            URL.create(
                "postgresql+psycopg",
                username=db["USER"],
                password=db["PASSWORD"],
                host=db["HOST"],
                port=int(db["PORT"]),
                database=db["NAME"],
            )
        )
        self.addCleanup(self.engine.dispose)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        self.alembic = Config()
        self.alembic.set_main_option(
            "script_location",
            str(Path(__file__).resolve().parents[2] / "ai_engine/alembic"),
        )
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.alembic.attributes["connection"] = conn
            command.upgrade(self.alembic, "head")
        self.addCleanup(self.drop_ai_tables)
        self.user = User.objects.create_user(username="investigator")
        self.organization = Organization.objects.create(name="Allowed")
        self.foreign = Organization.objects.create(name="Foreign")
        self.membership = Membership.objects.create(
            user=self.user, organization=self.organization
        )
        self.credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=issue_knowledge_token(self.membership)
        )
        self.context = AgentContext(
            user_id=self.user.pk,
            organization_id=self.organization.pk,
            request_id=uuid4(),
            task="Investigate revenue",
            permissions=frozenset({"knowledge.read"}),
        )
        self.document = self.make_document(self.organization, "Revenue is declining.")
        self.other_document = self.make_document(
            self.foreign, "FOREIGN revenue is rising."
        )

        class Provider(EmbeddingProvider):
            def embed_text(self, value):
                return [1.0, 0.0, 0.0]

        class LLM:
            def generate(self, **kwargs):
                return LLMResponse("Revenue is declining.", ())

        self.provider = Provider()
        self.config = EmbeddingConfig("local", "coordination-test", 3)
        self.knowledge = KnowledgeAgent(RAGService(LLM(), self.provider, self.config))
        with self.sessions() as db:
            DocumentChunkEmbeddingService(self.provider, self.config).upsert_chunks(
                db,
                [
                    DocumentChunkInput(chunk.pk, chunk.text)
                    for chunk in DocumentChunk.objects.all()
                ],
            )

    def drop_ai_tables(self):
        with self.engine.begin() as conn:
            conn.execute(text("DROP TABLE document_chunk_embeddings"))
            conn.execute(text("DROP TABLE alembic_version"))

    def make_document(self, organization, value):
        document = Document.objects.create(
            organization=organization,
            name="Report",
            storage_key=str(uuid4()),
            status="ready",
            embedding_status="ready",
        )
        DocumentChunk.objects.create(document=document, chunk_index=0, text=value)
        return document

    def reader(self, name="reader", **kwargs):
        return ReadAgent(
            name, self.credentials, self.sessions, self.document.pk, **kwargs
        )

    def coordinate(self, agents, context=None):
        registry = AgentRegistry()
        for agent in agents:
            registry.register(agent)
        return MultiAgentCoordinator(AgentSupervisor(registry)).execute(
            AgentSelection(
                tuple(agent.name for agent in agents), "Trusted explicit selection"
            ),
            context or self.context,
        )

    def test_authenticated_knowledge_and_read_tool_keep_evidence_and_tenant_scope(self):
        reader = self.reader()
        before = list(Document.objects.order_by("id").values())
        with self.sessions() as db:
            db.execute(text("SET TRANSACTION READ ONLY"))
            identity = authenticate_knowledge(self.credentials, db)
            context = replace(
                self.context,
                user_id=identity.user_id,
                organization_id=identity.organization_id,
                state={"db": db},
            )
            result = self.coordinate((self.knowledge, reader), context)
            db.rollback()
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.quality.agreement, "HIGH")
        self.assertIs(reader.contexts[0], context)
        chunk_id = self.document.chunks.get().pk
        self.assertEqual(result.citations, (chunk_id, chunk_id))
        self.assertEqual(result.results[0].data["citations"], (chunk_id,))
        self.assertEqual(result.results[0].evidence[0]["document_chunk_id"], chunk_id)
        self.assertIn("similarity", result.results[0].evidence[0])
        self.assertNotIn("FOREIGN", repr(result))
        self.assertEqual(list(Document.objects.order_by("id").values()), before)

    def test_denied_agent_permission_is_partial_not_an_authorized_read(self):
        allowed, denied = self.reader("allowed"), self.reader("denied")
        denied.allowed_tools = ()
        result = self.coordinate((allowed, denied))
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.results[1].evidence, ())
        self.assertIn("AgentToolAccessError", result.results[1].errors[0])
        self.assertFalse(result.evaluations[1].passed)

    def test_context_grant_and_both_integer_identities_are_still_required(self):
        for changes in (
            {"permissions": frozenset()},
            {"organization_id": self.foreign.pk},
            {"user_id": self.user.pk + 99},
        ):
            with self.subTest(changes=changes):
                result = self.coordinate(
                    (self.reader(),), replace(self.context, **changes)
                )
                self.assertEqual(result.status, "failed")
                self.assertEqual(result.evidence, ())
                self.assertEqual(result.citations, ())

    def test_invalid_expired_and_revoked_credentials_do_not_produce_evidence(self):
        invalid = self.reader()
        invalid.credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="bad-secret"
        )
        result = self.coordinate((invalid,))
        self.assertEqual(result.status, "failed")
        self.assertNotIn("bad-secret", repr(result))
        KnowledgeAccessToken.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        result = self.coordinate((self.reader(),))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.evidence, ())
        KnowledgeAccessToken.objects.all().delete()
        self.assertEqual(self.coordinate((self.reader(),)).status, "failed")

    def test_token_revocation_between_agents_is_rechecked_by_tools(self):
        first = self.reader("first")
        execute = first.execute

        def read_then_revoke(context):
            result = execute(context)
            # Simulate an external revocation; the production coordinator never writes.
            KnowledgeAccessToken.objects.all().delete()
            return result

        first.execute = read_then_revoke
        result = self.coordinate((first, self.reader("second")))
        self.assertEqual(result.status, "partial")
        self.assertTrue(result.results[0].success)
        self.assertFalse(result.results[1].success)
        self.assertEqual(result.results[1].evidence, ())
        self.assertIn("HTTPException", result.results[1].errors[0])

    def test_foreign_document_read_is_incomplete_without_fabricated_conclusion(self):
        reader = ReadAgent(
            "foreign", self.credentials, self.sessions, self.other_document.pk
        )
        result = self.coordinate((reader,))
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.evidence, ())
        self.assertEqual(result.citations, ())
        self.assertEqual(result.quality.unsupported_claims, ("foreign",))
        self.assertIn("No supported conclusion", result.summary)

    def test_mutation_arguments_are_rejected_and_data_stays_unchanged(self):
        before = list(DocumentChunk.objects.order_by("id").values())
        result = self.coordinate((self.reader(arguments={"operation": "delete"}),))
        self.assertEqual(result.status, "failed")
        self.assertIn("ValidationError", result.results[0].errors[0])
        self.assertEqual(list(DocumentChunk.objects.order_by("id").values()), before)
        self.assertEqual(self.coordinate((self.reader(),)).status, "complete")
