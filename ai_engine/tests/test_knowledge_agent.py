import unittest
from unittest.mock import Mock
from uuid import uuid4

from sqlalchemy.orm import Session

from ai_engine.app.agents import (
    Agent,
    AgentContext,
    AgentResult,
    KnowledgeAgent,
)
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.services.context_assembly_service import (
    AssembledContext,
    ContextItem,
)
from ai_engine.app.services.rag_service import (
    RAGResponse,
    RAGService,
)


class KnowledgeAgentTests(unittest.TestCase):
    def setUp(self):
        self.rag_service = Mock(spec=RAGService)

        self.rag_service.answer.return_value = (
            RAGResponse(
                query="What is GROOT?",
                context=AssembledContext(
                    items=(
                        ContextItem(
                            document_chunk_id=42,
                            text="GROOT is an operational intelligence system.",
                            similarity=0.95,
                        ),
                    ),
                    text=(
                        "[Chunk 42 | similarity=0.9500]\n"
                        "GROOT is an operational intelligence system."
                    ),
                ),
                response=LLMResponse(
                    text=(
                        "GROOT is an operational intelligence system."
                    ),
                    tool_calls=(),
                ),
            )
        )

        self.agent = KnowledgeAgent(
            rag_service=self.rag_service,
        )

        self.db = Mock(spec=Session)

        self.context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="What is GROOT?",
            state={
                "db": self.db,
            },
        )

    def test_implements_agent_contract(self):
        self.assertIsInstance(
            self.agent,
            Agent,
        )

    def test_defines_knowledge_capabilities(self):
        self.assertEqual(
            self.agent.capabilities,
            (
                "search_documents",
                "retrieve_report",
                "search_company_knowledge",
            ),
        )

    def test_returns_standardized_result(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertIsInstance(
            result,
            AgentResult,
        )

        self.assertTrue(result.success)

        self.assertEqual(
            result.agent_name,
            "knowledge_agent",
        )

        self.assertEqual(
            result.summary,
            "GROOT is an operational intelligence system.",
        )

    def test_uses_task_as_default_query(self):
        self.agent.execute(
            self.context,
        )

        self.rag_service.answer.assert_called_once_with(
            db=self.db,
            query="What is GROOT?",
            top_k=5,
        )

    def test_allows_query_override(self):
        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="Original task",
            state={
                "db": self.db,
                "query": "Search company knowledge",
            },
        )

        self.agent.execute(context)

        self.rag_service.answer.assert_called_once_with(
            db=self.db,
            query="Search company knowledge",
            top_k=5,
        )

    def test_uses_requested_top_k(self):
        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="What is GROOT?",
            state={
                "db": self.db,
                "top_k": 3,
            },
        )

        self.agent.execute(context)

        self.rag_service.answer.assert_called_once_with(
            db=self.db,
            query="What is GROOT?",
            top_k=3,
        )

    def test_preserves_evidence_and_citations(self):
        result = self.agent.execute(
            self.context,
        )

        self.assertEqual(
            result.evidence,
            (
                {
                    "document_chunk_id": 42,
                    "text": (
                        "GROOT is an operational intelligence system."
                    ),
                    "similarity": 0.95,
                },
            ),
        )

        self.assertEqual(
            result.data["citations"],
            (42,),
        )

    def test_returns_failure_without_database_session(self):
        context = AgentContext(
            user_id=uuid4(),
            organization_id=uuid4(),
            request_id=uuid4(),
            task="What is GROOT?",
        )

        result = self.agent.execute(context)

        self.assertFalse(result.success)

        self.assertEqual(
            result.agent_name,
            "knowledge_agent",
        )

        self.assertEqual(
            result.errors,
            (
                "A SQLAlchemy Session must be provided in "
                "context.state['db'].",
            ),
        )

        self.rag_service.answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
