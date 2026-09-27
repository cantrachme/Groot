import json
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError
from sqlalchemy import delete, insert, text, update

from ai_engine.app.agents.context import AgentContext
from ai_engine.app.agents.knowledge import KnowledgeAgent
from ai_engine.app.core.authentication import KnowledgeIdentity
from ai_engine.app.core.context import AIRequestContext
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.llm.tool_call import ToolCall
from ai_engine.app.orchestration.orchestrator import Orchestrator
from ai_engine.app.permissions.models import Permission
from ai_engine.app.tools import tool_registry
from ai_engine.app.tools.health import HealthCheckTool
from ai_engine.app.tools.read_only.base import ReadOnlyToolRegistry
from ai_engine.app.tools.read_only.documents import ListDocumentsTool, documents
from ai_engine.app.tools.schema import build_tool_schemas


class ReadOnlyToolTests(unittest.TestCase):
    def setUp(self):
        self.agent = KnowledgeAgent(Mock())
        self.context = AgentContext(
            user_id=7,
            organization_id=11,
            request_id=uuid4(),
            task="inspect",
            permissions=frozenset({"knowledge.read"}),
        )
        self.credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="server-secret",
        )
        self.db = Mock()
        self.db.__enter__ = Mock(return_value=self.db)
        self.db.__exit__ = Mock(return_value=False)
        self.sessions = Mock(return_value=self.db)
        self.db.execute.return_value.mappings.return_value.all.return_value = []
        self.auth = patch(
            "ai_engine.app.tools.read_only.base.authenticate_knowledge",
            return_value=KnowledgeIdentity(7, 11, "member"),
        ).start()
        self.addCleanup(patch.stopall)
        self.registry = self.make_registry()

    def make_registry(self, context=None, agent=None):
        return (agent or self.agent).read_only_tools(
            context or self.context,
            self.credentials,
            session_factory=self.sessions,
        )

    def test_registration_and_discovery_preserve_global_registry(self):
        self.assertEqual(
            self.registry.list(), ["list_documents", "read_document_chunks"]
        )
        self.assertEqual(tool_registry.list(), ["health_check"])
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.registry.register(self.registry.get("list_documents"))
        with self.assertRaises(KeyError):
            self.registry.get("update_document")

    def test_schemas_expose_only_strict_read_arguments(self):
        schemas = build_tool_schemas(self.registry)
        first, second = [schema["function"]["parameters"] for schema in schemas]
        self.assertFalse(first["additionalProperties"])
        self.assertEqual(set(first["properties"]), {"limit", "after_id"})
        self.assertEqual(
            set(second["properties"]), {"limit", "document_id", "after_index"}
        )
        self.assertEqual(second["required"], ["document_id"])
        self.assertEqual(second["properties"]["limit"]["maximum"], 20)
        self.assertNotIn("server-secret", json.dumps(schemas))
        self.assertEqual(
            build_tool_schemas(tool_registry)[0]["function"]["parameters"],
            {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        )

    def test_rejects_non_read_definitions(self):
        registry = ReadOnlyToolRegistry()
        with self.assertRaises(TypeError):
            registry.register(HealthCheckTool())
        for statement in (
            update(documents),
            delete(documents),
            insert(documents),
            text("SELECT 1"),
        ):
            with self.subTest(statement=type(statement).__name__):
                tool = self.registry.get("list_documents")
                tool.statement = statement
                with self.assertRaisesRegex(TypeError, "SELECT"):
                    registry.register(tool)
                with self.assertRaises(TypeError):
                    tool.execute()
        self.sessions.assert_not_called()

    def test_rejects_write_permission_and_unguarded_executor(self):
        tool = self.registry.get("list_documents")
        tool.permission = Permission("knowledge", "write")
        with self.assertRaisesRegex(ValueError, "knowledge.read"):
            ReadOnlyToolRegistry().register(tool)

        class Unguarded(ListDocumentsTool):
            def execute(self, **kwargs):
                return "unsafe"

        tool = Unguarded(
            credentials=self.credentials, agent=self.agent, context=self.context
        )
        with self.assertRaisesRegex(ValueError, "guarded"):
            ReadOnlyToolRegistry().register(tool)

    def test_rejects_mutation_scope_injection_and_invalid_bounds_before_db(self):
        attempts = (
            {"operation": "delete"},
            {"sql": "DELETE FROM core_document"},
            {"organization_id": 22},
            {"user_id": 8},
            {"permissions": ["knowledge.write"]},
            {"credentials": "fake"},
            {"name": "overwrite"},
            {"limit": 0},
            {"limit": 101},
            {"limit": True},
            {"limit": "2"},
            {"after_id": -1},
            {"after_id": 2**63},
        )
        for args in attempts:
            with self.subTest(args=args), self.assertRaises(ValidationError):
                self.registry.get("list_documents").execute(**args)
        for args in (
            {},
            {"document_id": True},
            {"document_id": 0},
            {"document_id": 1, "limit": 21},
            {"document_id": 1, "after_index": -2},
        ):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                self.registry.get("read_document_chunks").execute(**args)
        self.sessions.assert_not_called()

    def test_context_must_match_live_integer_identity(self):
        for changes in (
            {"user_id": 8},
            {"organization_id": 22},
            {"organization_id": uuid4()},
            {"user_id": True},
        ):
            with self.subTest(changes=changes), self.assertRaises(PermissionError):
                self.make_registry(replace(self.context, **changes)).get(
                    "list_documents"
                ).execute()
        self.db.rollback.assert_called()

    def test_requires_agent_allowlist_context_grant_and_live_role(self):
        with self.assertRaises(PermissionError):
            self.make_registry(replace(self.context, permissions=frozenset())).get(
                "list_documents"
            ).execute()
        self.agent.allowed_tools = ()
        with self.assertRaises(PermissionError):
            self.registry.get("list_documents").execute()
        self.agent.allowed_tools = ("list_documents",)
        self.auth.return_value = KnowledgeIdentity(7, 11, "unknown")
        with self.assertRaises(PermissionError):
            self.registry.get("list_documents").execute()

    def test_authentication_failure_rolls_back_and_closes(self):
        self.auth.side_effect = HTTPException(401)
        with self.assertRaises(HTTPException):
            self.registry.get("list_documents").execute()
        self.db.rollback.assert_called_once()
        self.db.__exit__.assert_called_once()
        self.assertEqual(
            str(self.db.execute.call_args_list[0].args[0]), "SET TRANSACTION READ ONLY"
        )
        self.db.commit.assert_not_called()

    def test_authorized_page_has_bound_scope_and_cursor(self):
        self.db.execute.return_value.mappings.return_value.all.return_value = [
            {"id": 12},
            {"id": 13},
        ]
        page = self.registry.get("list_documents").execute(limit=1, after_id=8)
        self.assertEqual(page, {"items": [{"id": 12}], "next_cursor": 12})
        self.auth.assert_called_once_with(self.credentials, self.db)
        query, params = self.db.execute.call_args.args
        self.assertIn("core_document.organization_id = :_organization_id", str(query))
        self.assertEqual(
            params,
            {"limit": 1, "after_id": 8, "_organization_id": 11, "_fetch_limit": 2},
        )
        self.db.rollback.assert_called_once()
        self.db.commit.assert_not_called()

    def test_existing_orchestrator_uses_guarded_tools_and_typed_schema(self):
        llm = Mock()
        llm.generate.side_effect = [
            LLMResponse("", (ToolCall("call-1", "list_documents", {}),)),
            LLMResponse("No documents.", ()),
        ]
        result = Orchestrator(llm, self.registry).handle(
            AIRequestContext(7, 11, self.context.request_id),
            "list my documents",
        )
        self.assertEqual(result.text, "No documents.")
        sent = llm.generate.call_args.kwargs
        self.assertEqual(
            json.loads(sent["tool_results"][0]["content"]),
            {"items": [], "next_cursor": None},
        )
        self.assertNotIn("server-secret", repr(llm.generate.call_args_list))
        self.auth.assert_called_once()

    def test_orchestrator_cannot_turn_read_into_write(self):
        llm = Mock()
        llm.generate.return_value = LLMResponse(
            "", (ToolCall("call-1", "list_documents", {"operation": "delete"}),)
        )
        with self.assertRaises(ValidationError):
            Orchestrator(llm, self.registry).handle(
                AIRequestContext(7, 11, self.context.request_id),
                "delete documents",
            )
        self.assertEqual(llm.generate.call_count, 1)
        self.sessions.assert_not_called()
