"""Exercise the guarded tools against the real Django PostgreSQL test database."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import URL, create_engine, func, select, text, update
from sqlalchemy.exc import InternalError
from sqlalchemy.orm import sessionmaker

from ai_engine.app.agents.context import AgentContext
from ai_engine.app.agents.knowledge import KnowledgeAgent
from ai_engine.app.tools.read_only.base import ReadOnlyToolRegistry
from ai_engine.app.tools.read_only.documents import ListDocumentsTool, documents

from .knowledge_tokens import issue_knowledge_token
from .models import (
    Document,
    DocumentChunk,
    KnowledgeAccessToken,
    Membership,
    Organization,
    User,
)


class ReadOnlyToolsPostgresTests(TransactionTestCase):
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
        self.user = User.objects.create_user(username="tool-member")
        self.organization = Organization.objects.create(name="Allowed")
        self.other = Organization.objects.create(name="Foreign")
        self.membership = Membership.objects.create(
            user=self.user, organization=self.organization
        )
        self.credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=issue_knowledge_token(self.membership),
        )
        self.context = AgentContext(
            user_id=self.user.pk,
            organization_id=self.organization.pk,
            request_id=uuid4(),
            task="inspect knowledge",
            permissions=frozenset({"knowledge.read"}),
        )
        self.agent = KnowledgeAgent(Mock())
        self.registry = self.make_registry()
        self.first = self.make_document(self.organization, "First")
        self.second = self.make_document(self.organization, "Second")
        self.foreign = self.make_document(self.other, "FOREIGN")

    def make_registry(self, context=None, credentials=None):
        return self.agent.read_only_tools(
            context or self.context,
            credentials or self.credentials,
            session_factory=self.sessions,
        )

    def make_document(self, organization, name, **kwargs):
        doc = Document.objects.create(
            organization=organization,
            name=name,
            storage_key=str(uuid4()),
            mime_type="text/plain",
            status=kwargs.get("status", "ready"),
            embedding_status=kwargs.get("embedding_status", "ready"),
        )
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(document=doc, chunk_index=i, text=f"{name} chunk {i}")
                for i in range(3)
            ]
        )
        return doc

    def test_authorized_listing_is_scoped_paginated_and_minimal(self):
        tool = self.registry.get("list_documents")
        first = tool.execute(limit=1)
        self.assertEqual([item["id"] for item in first["items"]], [self.first.pk])
        self.assertEqual(first["next_cursor"], self.first.pk)
        second = tool.execute(limit=1, after_id=first["next_cursor"])
        self.assertEqual([item["id"] for item in second["items"]], [self.second.pk])
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(
            set(first["items"][0]), {"id", "name", "document_type", "mime_type", "size"}
        )
        self.assertEqual(
            tool.execute(after_id=self.second.pk), {"items": [], "next_cursor": None}
        )

    def test_chunk_read_preserves_evidence_ids_order_and_cursor(self):
        tool = self.registry.get("read_document_chunks")
        page = tool.execute(document_id=self.first.pk, limit=2)
        self.assertEqual([item["chunk_index"] for item in page["items"]], [0, 1])
        self.assertEqual(page["next_cursor"], 1)
        self.assertEqual(
            page["items"][0],
            {
                "document_chunk_id": self.first.chunks.get(chunk_index=0).pk,
                "document_id": self.first.pk,
                "chunk_index": 0,
                "text": "First chunk 0",
                "truncated": False,
            },
        )
        last = tool.execute(
            document_id=self.first.pk, after_index=page["next_cursor"], limit=2
        )
        self.assertEqual([item["chunk_index"] for item in last["items"]], [2])
        self.assertIsNone(last["next_cursor"])

    def test_bounds_and_long_text_truncation(self):
        self.first.chunks.filter(chunk_index=0).update(text="😀" * 4001)
        self.first.chunks.filter(chunk_index=1).update(text="x" * 4000)
        page = self.registry.get("read_document_chunks").execute(
            document_id=self.first.pk
        )
        self.assertEqual(page["items"][0]["text"], "😀" * 4000)
        self.assertTrue(page["items"][0]["truncated"])
        self.assertFalse(page["items"][1]["truncated"])
        for name, args in (
            ("list_documents", {"limit": 101}),
            ("read_document_chunks", {"document_id": self.first.pk, "limit": 21}),
        ):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.registry.get(name).execute(**args)

    def test_foreign_missing_and_unready_documents_are_indistinguishable(self):
        hidden = [self.foreign.pk, 9223372036854775807]
        for status in ("pending", "processing", "failed"):
            hidden.append(
                self.make_document(self.organization, status, status=status).pk
            )
            hidden.append(
                self.make_document(
                    self.organization, status, embedding_status=status
                ).pk
            )
        tool = self.registry.get("read_document_chunks")
        for document_id in hidden:
            with self.subTest(document_id=document_id):
                self.assertEqual(
                    tool.execute(document_id=document_id),
                    {"items": [], "next_cursor": None},
                )
        self.assertEqual(
            [
                item["id"]
                for item in self.registry.get("list_documents").execute()["items"]
            ],
            [self.first.pk, self.second.pk],
        )

    def test_same_user_multiple_memberships_cannot_select_tenant_with_arguments(self):
        membership = Membership.objects.create(user=self.user, organization=self.other)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=issue_knowledge_token(membership)
        )
        with self.assertRaises(PermissionError):
            self.make_registry(credentials=credentials).get("list_documents").execute()
        with self.assertRaises(PermissionError):
            self.make_registry(
                replace(self.context, organization_id=self.other.pk)
            ).get("list_documents").execute()
        other_registry = self.make_registry(
            replace(self.context, organization_id=self.other.pk), credentials
        )
        self.assertEqual(
            [
                item["id"]
                for item in other_registry.get("list_documents").execute()["items"]
            ],
            [self.foreign.pk],
        )
        self.assertEqual(
            other_registry.get("read_document_chunks").execute(
                document_id=self.first.pk
            )["items"],
            [],
        )
        with self.assertRaises(ValidationError):
            self.registry.get("list_documents").execute(organization_id=self.other.pk)

    def test_missing_invalid_and_wrong_scheme_credentials(self):
        for credentials in (
            None,
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid"),
            HTTPAuthorizationCredentials(
                scheme="Basic", credentials=self.credentials.credentials
            ),
        ):
            registry = self.agent.read_only_tools(
                self.context, credentials, session_factory=self.sessions
            )
            for name, args in (
                ("list_documents", {}),
                ("read_document_chunks", {"document_id": self.first.pk}),
            ):
                with (
                    self.subTest(credentials=credentials is None, name=name),
                    self.assertRaises(HTTPException) as error,
                ):
                    registry.get(name).execute(**args)
                self.assertEqual(error.exception.status_code, 401)

    def test_registry_rechecks_token_expiry_and_revocation_each_call(self):
        tool = self.registry.get("list_documents")
        self.assertEqual(len(tool.execute()["items"]), 2)
        KnowledgeAccessToken.objects.update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        with self.assertRaises(HTTPException):
            tool.execute()
        KnowledgeAccessToken.objects.update(
            expires_at=timezone.now() + timedelta(hours=1)
        )
        self.assertEqual(len(tool.execute()["items"]), 2)
        KnowledgeAccessToken.objects.all().delete()
        with self.assertRaises(HTTPException):
            tool.execute()

    def test_registry_rechecks_user_and_membership(self):
        tool = self.registry.get("read_document_chunks")
        self.user.is_active = False
        self.user.save()
        with self.assertRaises(HTTPException):
            tool.execute(document_id=self.first.pk)
        self.user.is_active = True
        self.user.save()
        self.assertEqual(len(tool.execute(document_id=self.first.pk)["items"]), 3)
        self.membership.delete()
        with self.assertRaises(HTTPException):
            tool.execute(document_id=self.first.pk)

    def test_live_role_context_permission_and_agent_allowlist_are_all_required(self):
        tool = self.registry.get("list_documents")
        for role in ("member", "admin"):
            self.membership.role = role
            self.membership.save()
            self.assertEqual(len(tool.execute()["items"]), 2)
        self.membership.role = "unknown"
        self.membership.save()
        with self.assertRaises(PermissionError):
            tool.execute()
        self.membership.role = "member"
        self.membership.save()
        with self.assertRaises(PermissionError):
            self.make_registry(replace(self.context, permissions=frozenset())).get(
                "list_documents"
            ).execute()
        self.agent.allowed_tools = ()
        with self.assertRaises(PermissionError):
            tool.execute()

    def test_read_transaction_is_database_enforced_and_does_not_persist(self):
        class InspectTransaction(ListDocumentsTool):
            statement = select(
                documents.c.id,
                func.current_setting("transaction_read_only").label("read_only"),
            )

        tool = InspectTransaction(
            credentials=self.credentials,
            agent=self.agent,
            context=self.context,
            session_factory=self.sessions,
        )
        registry = ReadOnlyToolRegistry()
        registry.register(tool)
        self.assertTrue(
            all(item["read_only"] == "on" for item in tool.execute()["items"])
        )
        with self.sessions() as db:
            self.assertEqual(
                db.execute(text("SHOW transaction_read_only")).scalar_one(), "off"
            )

    def test_hidden_mutation_in_select_is_blocked_by_postgres_and_rolled_back(self):
        class MutatingSelect(ListDocumentsTool):
            # A trusted extension bug must still fail at the database boundary.
            statement = ListDocumentsTool.statement.add_cte(
                update(documents)
                .values(name="CORRUPTED")
                .returning(documents.c.id)
                .cte("write_attempt"),
            )

        tool = MutatingSelect(
            credentials=self.credentials,
            agent=self.agent,
            context=self.context,
            session_factory=self.sessions,
        )
        registry = ReadOnlyToolRegistry()
        registry.register(tool)
        before = list(Document.objects.order_by("id").values())
        with self.assertRaises(InternalError) as error:
            tool.execute()
        self.assertEqual(error.exception.orig.sqlstate, "25006")
        self.assertEqual(list(Document.objects.order_by("id").values()), before)
        self.assertEqual(len(self.registry.get("list_documents").execute()["items"]), 2)

    def test_reads_and_rejected_mutation_arguments_leave_application_rows_unchanged(
        self,
    ):
        models = (
            Document,
            DocumentChunk,
            KnowledgeAccessToken,
            Membership,
            Organization,
            User,
        )
        before = {
            model: list(model.objects.order_by("pk").values()) for model in models
        }
        self.registry.get("list_documents").execute()
        self.registry.get("read_document_chunks").execute(document_id=self.first.pk)
        for name, args in (
            ("list_documents", {"operation": "delete"}),
            (
                "read_document_chunks",
                {"document_id": self.first.pk, "text": "overwrite"},
            ),
        ):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.registry.get(name).execute(**args)
        self.assertEqual(
            {model: list(model.objects.order_by("pk").values()) for model in models},
            before,
        )
