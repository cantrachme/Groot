import hashlib
import io
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from celery.exceptions import Retry
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from kombu.exceptions import OperationalError as BrokerError

from .documents.tasks import (
    embed_document,
    enqueue_document_embeddings,
    process_document,
)
from .knowledge_tokens import issue_knowledge_token
from .models import Document, KnowledgeAccessToken, Membership, Organization, User

ROOT = Path(__file__).resolve().parents[2]


class KnowledgeTokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="member")
        self.organization = Organization.objects.create(name="Token org")
        self.membership = Membership.objects.create(
            user=self.user, organization=self.organization
        )

    def test_only_digest_is_stored_and_tokens_are_unique(self):
        raw = issue_knowledge_token(self.membership)
        other = issue_knowledge_token(self.membership)
        self.assertNotEqual(raw, other)
        record = KnowledgeAccessToken.objects.get(
            digest=hashlib.sha256(raw.encode()).hexdigest()
        )
        self.assertNotEqual(record.digest, raw)
        self.assertEqual(record.membership, self.membership)
        self.assertGreater(record.expires_at, timezone.now() + timedelta(hours=23))

    def test_disabled_user_cannot_receive_token(self):
        self.user.is_active = False
        self.user.save()
        with self.assertRaisesRegex(ValueError, "active user"):
            issue_knowledge_token(self.membership)
        self.assertEqual(KnowledgeAccessToken.objects.count(), 0)

    def test_lifetime_bounds(self):
        for hours in (0, 169):
            with self.assertRaises(ValueError):
                issue_knowledge_token(self.membership, hours=hours)
        self.assertEqual(KnowledgeAccessToken.objects.count(), 0)

    def test_command_issues_for_existing_membership_only(self):
        output = io.StringIO()
        call_command(
            "issue_knowledge_token",
            username=self.user.username,
            organization_id=self.organization.pk,
            hours=1,
            stdout=output,
        )
        digest = hashlib.sha256(output.getvalue().strip().encode()).hexdigest()
        self.assertTrue(KnowledgeAccessToken.objects.filter(digest=digest).exists())
        with self.assertRaises(CommandError):
            call_command(
                "issue_knowledge_token",
                username="missing",
                organization_id=self.organization.pk,
            )

    def test_deleting_membership_revokes_credentials(self):
        issue_knowledge_token(self.membership)
        self.membership.delete()
        self.assertFalse(KnowledgeAccessToken.objects.exists())


class EmbeddingHandoffTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Handoff org")
        self.document = Document.objects.create(
            organization=self.organization,
            name="note",
            mime_type="text/plain",
            storage_key="note",
        )

    def test_job_dispatched_only_after_commit(self):
        with patch.object(embed_document, "delay") as dispatch:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                result = process_document.run(self.document.pk, b"Company facts")
                dispatch.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            dispatch.assert_called_once_with(self.document.pk)
        self.assertTrue(result["success"])
        self.document.refresh_from_db()
        self.assertEqual(self.document.embedding_status, "pending")

    def test_rollback_does_not_publish_job(self):
        with patch.object(embed_document, "delay") as dispatch:
            with (
                self.captureOnCommitCallbacks(execute=True) as callbacks,
                self.assertRaises(RuntimeError),
                transaction.atomic(),
            ):
                process_document.run(self.document.pk, b"Company facts")
                raise RuntimeError("rollback")
            self.assertEqual(callbacks, [])
            dispatch.assert_not_called()
        self.assertFalse(self.document.chunks.exists())

    def test_failed_extraction_does_not_dispatch(self):
        self.document.mime_type = "unknown"
        self.document.save()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            result = process_document.run(self.document.pk, b"bad")
        self.assertEqual(callbacks, [])
        self.assertFalse(result["success"])
        self.document.refresh_from_db()
        self.assertEqual(self.document.embedding_status, "failed")

    def test_broker_failure_is_recorded(self):
        with patch.object(embed_document, "delay", side_effect=BrokerError("offline")):
            enqueue_document_embeddings(self.document.pk)
        self.document.refresh_from_db()
        self.assertEqual(self.document.embedding_status, "failed")
        self.assertIn("dispatch failed", self.document.embedding_error)

    def test_provider_failure_records_status_and_requests_bounded_retry(self):
        self.document.status = "ready"
        self.document.save()
        with (
            patch(
                "core.documents.tasks.persist_document_embeddings",
                side_effect=RuntimeError("provider down"),
            ),
            patch.object(embed_document, "retry", side_effect=Retry()) as retry,
            self.assertRaises(Retry),
        ):
            embed_document.run(self.document.pk)
        self.document.refresh_from_db()
        self.assertEqual(self.document.embedding_status, "failed")
        self.assertEqual(retry.call_args.kwargs["max_retries"], 3)
        self.assertIn("countdown", retry.call_args.kwargs)

    def test_missing_or_unready_document_does_not_embed(self):
        with patch("core.documents.tasks.persist_document_embeddings") as persist:
            self.assertFalse(embed_document.run(self.document.pk)["success"])
            self.document.delete()
            self.assertFalse(embed_document.run(self.document.pk or -1)["success"])
        persist.assert_not_called()

    def test_worker_autodiscovery_registers_nested_tasks(self):
        script = (
            "from config.celery import app; app.loader.import_default_modules(); "
            "assert {'core.documents.tasks.process_document', "
            "'core.documents.tasks.embed_document', 'core.ingestion.tasks.ingest_integration', "
            "'core.tasks.health_check_task'} <= set(app.tasks)"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT / "backend",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class KnowledgeFlowPostgresTests(TransactionTestCase):
    """Real Django + Alembic tables, pgvector and HTTP; only external providers are fake."""

    def setUp(self):
        from alembic import command
        from alembic.config import Config
        from fastapi.testclient import TestClient
        from sqlalchemy import URL, create_engine, text
        from sqlalchemy.orm import sessionmaker

        from ai_engine.app.agents.knowledge import KnowledgeAgent
        from ai_engine.app.db.dependencies import get_db
        from ai_engine.app.embeddings import EmbeddingConfig, EmbeddingProvider
        from ai_engine.app.llm.response import LLMResponse
        from ai_engine.app.main import app, get_knowledge_agent
        from ai_engine.app.services.rag_service import RAGService

        db = connection.settings_dict
        # Explicitly target only the database selected by Django's test runner.
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
        self.sessions = sessionmaker(bind=self.engine)
        self.alembic = Config()
        self.alembic.set_main_option("script_location", str(ROOT / "ai_engine/alembic"))
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            self.alembic.attributes["connection"] = conn
            command.upgrade(self.alembic, "head")

        class Provider(EmbeddingProvider):
            def embed_text(self, value):
                return [1.0, 0.0, 0.0]

            def embed_texts(self, texts):
                return [
                    [1.0, 0.0, 0.0] if "FOREIGN" in value else [0.8, 0.6, 0.0]
                    for value in texts
                ]

        class LLM:
            def __init__(self):
                self.calls = []

            def generate(self, **kwargs):
                self.calls.append(kwargs)
                return LLMResponse(
                    text="Answer grounded in supplied evidence.", tool_calls=()
                )

        self.provider, self.llm = Provider(), LLM()
        self.config = EmbeddingConfig("local", "integration", 3)
        self.rag = RAGService(self.llm, self.provider, self.config)
        self.app = app
        self.overrides = app.dependency_overrides.copy()

        def test_session():
            with self.sessions() as session:
                yield session

        app.dependency_overrides[get_db] = test_session
        app.dependency_overrides[get_knowledge_agent] = lambda: KnowledgeAgent(self.rag)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.env_patch = patch.dict(
            os.environ,
            {
                "EMBEDDING_PROVIDER": "local",
                "EMBEDDING_MODEL": "integration",
                "EMBEDDING_DIMENSIONS": "3",
            },
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.session_patch = patch(
            "ai_engine.app.db.database.SessionLocal", self.sessions
        )
        self.session_patch.start()
        self.addCleanup(self.session_patch.stop)
        self.provider_patch = patch(
            "ai_engine.app.embeddings.factory.build_embedding_provider",
            return_value=self.provider,
        )
        self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)
        self.user = User.objects.create_user(username="integration-user")
        self.organization = Organization.objects.create(name="Authorized org")
        self.other = Organization.objects.create(name="Foreign org")
        self.membership = Membership.objects.create(
            user=self.user, organization=self.organization
        )
        self.token = issue_knowledge_token(self.membership)

    def tearDown(self):
        from sqlalchemy import text

        self.app.dependency_overrides.clear()
        self.app.dependency_overrides.update(self.overrides)
        # AI tables are not owned by Django's flush; remove them before its teardown.
        with self.engine.begin() as conn:
            conn.execute(text("DROP TABLE document_chunk_embeddings"))
            conn.execute(text("DROP TABLE alembic_version"))
        self.engine.dispose()
        super().tearDown()

    def make_document(self, organization, content):
        document = Document.objects.create(
            organization=organization,
            name="note",
            storage_key=str(uuid4()),
            mime_type="text/plain",
        )
        with patch.object(embed_document, "delay") as dispatch:
            process_document.run(document.pk, content)
            dispatch.assert_called_once_with(document.pk)
        self.assertTrue(embed_document.run(document.pk)["success"])
        return document

    def ask(self, **fields):
        return self.client.post(
            "/rag",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "request_id": str(uuid4()),
                "message": "What are our facts?",
                **fields,
            },
        )

    def test_extraction_to_scoped_answer_excludes_better_foreign_match(self):
        own = self.make_document(self.organization, b"OUR company facts")
        foreign = self.make_document(self.other, b"FOREIGN secret facts")
        response = self.ask(top_k=1)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(
            body["citations"], list(own.chunks.values_list("id", flat=True))
        )
        self.assertNotIn("FOREIGN", str(body))
        self.assertIn("OUR company facts", body["evidence"][0]["text"])
        self.assertNotIn("FOREIGN", self.llm.calls[0]["user_message"])
        from ai_engine.app.services.rag_document_service import RAGDocumentService

        with self.sessions() as db:
            self.assertEqual(
                RAGDocumentService().get_chunk_texts(
                    db,
                    list(foreign.chunks.values_list("id", flat=True)),
                    self.organization.pk,
                ),
                {},
            )

    def test_no_documents_returns_insufficient_context_without_llm(self):
        self.make_document(self.other, b"FOREIGN only")
        response = self.ask()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["evidence"], [])
        self.assertIn(
            "not enough document context", response.json()["response"]["text"]
        )
        self.assertEqual(self.llm.calls, [])

    def test_invalid_expired_revoked_and_disabled_credentials_are_denied(self):
        original = self.token
        self.token = "invalid"
        self.assertEqual(self.ask().status_code, 401)
        self.token = original
        KnowledgeAccessToken.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.ask().status_code, 401)
        self.token = issue_knowledge_token(self.membership)
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.ask().status_code, 401)
        self.user.is_active = True
        self.user.save()
        self.membership.delete()
        self.assertEqual(self.ask().status_code, 401)
        self.assertEqual(self.llm.calls, [])

    def test_retry_upserts_existing_vectors(self):
        from sqlalchemy import select

        from ai_engine.app.models import DocumentChunkEmbedding

        document = self.make_document(self.organization, b"OUR facts")
        with self.sessions() as db:
            before = db.execute(select(DocumentChunkEmbedding)).scalars().all()
            ids = [row.id for row in before]
        self.assertTrue(embed_document.run(document.pk)["success"])
        with self.sessions() as db:
            after = db.execute(select(DocumentChunkEmbedding)).scalars().all()
            self.assertEqual([row.id for row in after], ids)
        self.assertEqual(len(ids), document.chunks.count())

    def test_embedding_holds_document_lock_against_concurrent_reprocessing(self):
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError

        from .documents.tasks import persist_document_embeddings

        document = self.make_document(self.organization, b"OUR locked facts")

        def verify_lock_then_persist(chunks):
            with self.sessions() as db, self.assertRaises(OperationalError):
                db.execute(
                    text(
                        "SELECT id FROM core_document WHERE id = :id FOR UPDATE NOWAIT"
                    ),
                    {"id": document.pk},
                )
            persist_document_embeddings(chunks)

        with patch(
            "core.documents.tasks.persist_document_embeddings",
            side_effect=verify_lock_then_persist,
        ):
            self.assertTrue(embed_document.run(document.pk)["success"])

    def test_reprocessing_removes_stale_vectors_before_new_job(self):
        from sqlalchemy import select

        from ai_engine.app.models import DocumentChunkEmbedding

        document = self.make_document(self.organization, b"OUR old facts")
        old_ids = list(document.chunks.values_list("id", flat=True))
        with patch.object(embed_document, "delay"):
            process_document.run(document.pk, b"OUR replacement facts")
        with self.sessions() as db:
            self.assertEqual(
                db.execute(select(DocumentChunkEmbedding)).scalars().all(), []
            )
        self.assertEqual(self.ask().json()["evidence"], [])
        embed_document.run(document.pk)
        body = self.ask().json()
        self.assertIn("replacement facts", body["context"])
        self.assertFalse(set(old_ids) & set(body["citations"]))

    def test_document_deletion_cascades_vectors(self):
        from sqlalchemy import select

        from ai_engine.app.models import DocumentChunkEmbedding

        document = self.make_document(self.organization, b"OUR deleted facts")
        document.delete()
        with self.sessions() as db:
            self.assertEqual(
                db.execute(select(DocumentChunkEmbedding)).scalars().all(), []
            )
        self.assertEqual(self.ask().json()["evidence"], [])

    def test_failed_extraction_removes_old_vectors(self):
        from sqlalchemy import select

        from ai_engine.app.models import DocumentChunkEmbedding

        document = self.make_document(self.organization, b"OUR old facts")
        document.mime_type = "unknown"
        document.save()
        self.assertFalse(process_document.run(document.pk, b"bad")["success"])
        with self.sessions() as db:
            self.assertEqual(
                db.execute(select(DocumentChunkEmbedding)).scalars().all(), []
            )
        self.assertEqual(self.ask().json()["evidence"], [])

    def test_upsert_rolls_back_partial_writes_on_foreign_key_error(self):
        from sqlalchemy import func, select
        from sqlalchemy.exc import IntegrityError

        from ai_engine.app.models import DocumentChunkEmbedding
        from ai_engine.app.services.embedding_service import EmbeddingService

        document = self.make_document(self.organization, b"OUR facts")
        chunk_id = document.chunks.get().pk
        other_config = type(self.config)("local", "other-model", 3)
        with self.sessions() as db:
            with self.assertRaises(IntegrityError):
                EmbeddingService(self.provider, other_config).upsert_chunks(
                    db,
                    [(chunk_id, "valid"), (2147483647, "missing chunk")],
                )
            self.assertEqual(
                db.scalar(
                    select(func.count())
                    .select_from(DocumentChunkEmbedding)
                    .where(DocumentChunkEmbedding.model == "other-model")
                ),
                0,
            )

    def test_migration_cleans_legacy_orphans_and_preserves_django_tables(self):
        from alembic import command
        from sqlalchemy import text

        with self.engine.begin() as conn:
            self.alembic.attributes["connection"] = conn
            command.downgrade(self.alembic, "a66f2147d28c")
            conn.execute(
                text("""INSERT INTO document_chunk_embeddings
                (document_chunk_id, model, dimensions, embedding, created_at, updated_at)
                VALUES (2147483647, 'orphan', 3, '[1,0,0]', NOW(), NOW())""")
            )
            command.upgrade(self.alembic, "head")
            self.assertEqual(
                conn.scalar(text("SELECT count(*) FROM document_chunk_embeddings")), 0
            )
            self.assertEqual(
                conn.scalar(text("SELECT count(*) FROM core_organization")), 2
            )
            command.check(self.alembic)

    def test_unscoped_services_cannot_read_stored_documents(self):
        from ai_engine.app.services.rag_document_service import RAGDocumentService
        from ai_engine.app.services.similarity_search_service import (
            SimilaritySearchService,
        )

        document = self.make_document(self.organization, b"OUR secret facts")
        with self.sessions() as db:
            self.assertEqual(
                SimilaritySearchService().search(db, [1, 0, 0], "integration", 3), []
            )
            self.assertEqual(
                RAGDocumentService().get_chunk_texts(db, [document.chunks.get().pk]), {}
            )
