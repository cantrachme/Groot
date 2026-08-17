import unittest
from unittest.mock import Mock

from ai_engine.app.embeddings import EmbeddingConfig, EmbeddingProvider
from ai_engine.app.llm.provider import LLMProvider
from ai_engine.app.llm.response import LLMResponse
from ai_engine.app.models import DocumentChunkEmbedding
from ai_engine.app.services.context_assembly_service import (
    AssembledContext,
    ContextAssemblyService,
)
from ai_engine.app.services.rag_service import (
    RAGResponse,
    RAGService,
)
from ai_engine.app.services.retrieval_service import (
    RetrievalResult,
)
from ai_engine.app.services.similarity_search_service import (
    SimilaritySearchResult,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed_text(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def generate(
        self,
        system_prompt: str,
        user_message: str,
        tools: list[dict] | None = None,
        tool_results: list[dict] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "tools": tools,
                "tool_results": tool_results,
            }
        )

        return LLMResponse(
            text="The answer is in the document context.",
            tool_calls=(),
        )


class RAGServiceTests(unittest.TestCase):
    def make_retrieval_service(self):
        retrieval_service = Mock()

        embedding = DocumentChunkEmbedding(
            id=1,
            document_chunk_id=42,
            model="test-model",
            dimensions=3,
            embedding=[0.1, 0.2, 0.3],
        )

        retrieval_service.retrieve.return_value = RetrievalResult(
            query="What is this?",
            results=(
                SimilaritySearchResult(
                    embedding=embedding,
                    distance=0.1,
                    similarity=0.9,
                ),
            ),
        )

        return retrieval_service

    def test_retrieves_context_and_generates_answer(self):
        llm_provider = FakeLLMProvider()

        retrieval_service = self.make_retrieval_service()

        context_assembly = ContextAssemblyService()

        service = RAGService(
            llm_provider=llm_provider,
            embedding_provider=FakeEmbeddingProvider(),
            embedding_config=EmbeddingConfig(
                provider="fake",
                model="test-model",
                dimensions=3,
            ),
            retrieval_service=retrieval_service,
            context_assembly=context_assembly,
        )

        result = service.answer(
            db=Mock(),
            query="What is this?",
            chunk_texts={
                42: "This document describes GROOT.",
            },
            top_k=3,
        )

        self.assertIsInstance(
            result,
            RAGResponse,
        )

        self.assertEqual(
            result.query,
            "What is this?",
        )

        self.assertIsInstance(
            result.context,
            AssembledContext,
        )

        self.assertIn(
            "This document describes GROOT.",
            result.context.text,
        )

        self.assertEqual(
            result.response.text,
            "The answer is in the document context.",
        )

        retrieval_service.retrieve.assert_called_once_with(
            db=result.context and retrieval_service.retrieve.call_args.kwargs["db"],
            query="What is this?",
            top_k=3,
        )

        self.assertEqual(
            len(llm_provider.calls),
            1,
        )

        llm_call = llm_provider.calls[0]

        self.assertIn(
            "What is this?",
            llm_call["user_message"],
        )

        self.assertIn(
            "This document describes GROOT.",
            llm_call["user_message"],
        )

        self.assertIsNone(
            llm_call["tools"],
        )

        self.assertIsNone(
            llm_call["tool_results"],
        )

    def test_rejects_empty_query(self):
        llm_provider = Mock(spec=LLMProvider)
        retrieval_service = Mock()

        service = RAGService(
            llm_provider=llm_provider,
            embedding_provider=FakeEmbeddingProvider(),
            embedding_config=EmbeddingConfig(
                provider="fake",
                model="test-model",
                dimensions=3,
            ),
            retrieval_service=retrieval_service,
        )

        with self.assertRaisesRegex(
            ValueError,
            "query must not be empty",
        ):
            service.answer(
                db=Mock(),
                query="   ",
                chunk_texts={},
            )

        retrieval_service.retrieve.assert_not_called()
        llm_provider.generate.assert_not_called()

    def test_uses_default_top_k(self):
        llm_provider = FakeLLMProvider()
        retrieval_service = self.make_retrieval_service()

        service = RAGService(
            llm_provider=llm_provider,
            embedding_provider=FakeEmbeddingProvider(),
            embedding_config=EmbeddingConfig(
                provider="fake",
                model="test-model",
                dimensions=3,
            ),
            retrieval_service=retrieval_service,
        )

        service.answer(
            db=Mock(),
            query="hello",
            chunk_texts={42: "hello"},
        )

        self.assertEqual(
            retrieval_service.retrieve.call_args.kwargs["top_k"],
            5,
        )


if __name__ == "__main__":
    unittest.main()
